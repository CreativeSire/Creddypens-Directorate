from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.agents.prompts import inject_domain_block, system_prompt_for_agent
from app.integrations.email import email_integration
from app.integrations.slack import slack_integration
from app.integrations.webhook import webhook_integration
from app.llm.litellm_client import LLMError, execute_via_litellm
from app.models import AgentCatalog, HiredAgent
from app.schemas_execute import ExecuteContext
from app.settings import settings

_VAR_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


@dataclass
class EngineStepResult:
    step_index: int
    step_id: str
    agent_code: str
    input_message: str
    response: str
    model_used: str
    latency_ms: int
    trace_id: str


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_definition(self, definition: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        steps = definition.get("steps")
        if not isinstance(steps, list) or not steps:
            return ["workflow_definition.steps must be a non-empty list"]
        ids: set[str] = set()
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"steps[{idx}] must be an object")
                continue
            step_id = str(step.get("id") or "").strip()
            if not step_id:
                errors.append(f"steps[{idx}].id is required")
            elif step_id in ids:
                errors.append(f"duplicate step id: {step_id}")
            else:
                ids.add(step_id)
            if not str(step.get("agent_code") or "").strip():
                errors.append(f"steps[{idx}].agent_code is required")
        # Validate references
        for idx, step in enumerate(steps):
            condition = step.get("conditions") or {}
            if isinstance(condition, dict):
                for key in ("true", "false", "next"):
                    target = str(condition.get(key) or "").strip()
                    if target and target not in ids:
                        errors.append(f"steps[{idx}].conditions.{key} references unknown step id '{target}'")
            next_id = str(step.get("next") or "").strip()
            if next_id and next_id not in ids:
                errors.append(f"steps[{idx}].next references unknown step id '{next_id}'")
        return errors

    def resolve_variables(self, text_value: str, variables: dict[str, Any]) -> str:
        if not text_value:
            return ""

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            value = variables.get(key, "")
            return str(value)

        return _VAR_PATTERN.sub(repl, text_value)

    def evaluate_condition(self, expr: str, variables: dict[str, Any]) -> bool:
        expression = (expr or "").strip()
        if not expression:
            return True
        hydrated = self.resolve_variables(expression, variables)
        try:
            allowed = {"True": True, "False": False}
            return bool(eval(hydrated, {"__builtins__": {}}, allowed))  # noqa: S307
        except Exception:
            return False

    def get_next_step(self, *, current_step: dict[str, Any], condition_result: bool, order: list[str], current_index: int) -> str | None:
        conditions = current_step.get("conditions") or {}
        if isinstance(conditions, dict):
            if condition_result:
                true_target = str(conditions.get("true") or conditions.get("next") or "").strip()
                if true_target:
                    return true_target
            else:
                false_target = str(conditions.get("false") or "").strip()
                if false_target:
                    return false_target
        explicit_next = str(current_step.get("next") or "").strip()
        if explicit_next:
            return explicit_next
        if current_index + 1 < len(order):
            return order[current_index + 1]
        return None

    def execute_workflow(
        self,
        *,
        org_id: str,
        session_id: str,
        initial_message: str,
        context: ExecuteContext,
        workflow_definition: dict[str, Any],
    ) -> tuple[str, list[EngineStepResult]]:
        errors = self.validate_definition(workflow_definition)
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

        steps = workflow_definition["steps"]
        step_by_id = {str(step["id"]): step for step in steps}
        order = [str(step["id"]) for step in steps]
        max_steps = max(1, int(settings.workflow_max_steps))
        variables: dict[str, Any] = {"initial_message": initial_message, "previous_response": initial_message}
        current_id = str(workflow_definition.get("start_step_id") or order[0])
        results: list[EngineStepResult] = []
        safety_counter = 0

        while current_id:
            safety_counter += 1
            if safety_counter > max_steps:
                raise HTTPException(status_code=400, detail=f"Workflow exceeded max step limit ({max_steps})")

            step = step_by_id.get(current_id)
            if not step:
                break
            step_index = len(results) + 1
            agent_code = str(step.get("agent_code") or "").strip()
            action = str(step.get("action") or "").strip().lower()
            action_config = dict(step.get("action_config") or {})
            integration_id = str(step.get("integration_id") or "").strip()
            agent = self.db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent not found in workflow step {step_index}: {agent_code}")

            hired = (
                self.db.execute(
                    select(HiredAgent)
                    .where(HiredAgent.org_id == org_id)
                    .where(HiredAgent.agent_code == agent_code)
                    .where(HiredAgent.status == "active")
                )
                .scalars()
                .first()
            )
            if not hired:
                raise HTTPException(status_code=403, detail=f"Agent not hired for step {step_index}: {agent_code}")

            input_template = str(step.get("input") or step.get("message") or "").strip()
            if not input_template:
                input_template = "{{previous_response}}"
            input_message = self.resolve_variables(input_template, variables).strip()
            if not input_message:
                input_message = str(variables.get("previous_response") or initial_message)

            trace_id = str(uuid.uuid4())
            if action in {"slack", "email", "webhook"}:
                response_text = self._execute_integration_action(
                    action=action,
                    integration_id=integration_id,
                    input_message=input_message,
                    action_config=action_config,
                )
                result = {
                    "response": response_text,
                    "model_used": f"workflow/{action}",
                    "latency_ms": 0,
                    "tokens_used": 0,
                    "trace_id": trace_id,
                }
            else:
                system_prompt = (agent.system_prompt or "").strip() or system_prompt_for_agent(agent_code)
                system_prompt = inject_domain_block(system_prompt, agent)
                try:
                    result = execute_via_litellm(
                        provider=agent.llm_provider or "",
                        model=agent.llm_model or "",
                        system=system_prompt,
                        user=input_message,
                        trace_id=trace_id,
                        enable_search=bool(context.web_search),
                        enable_docs=bool(context.doc_retrieval),
                        org_id=org_id,
                        session_id=session_id,
                        agent_code=agent_code,
                    )
                except LLMError as exc:
                    raise HTTPException(status_code=503, detail=f"Workflow step {step_index} failed: {exc}") from exc
                response_text = result.get("response") or result.get("content") or result.get("text") or ""
            variables["previous_response"] = response_text
            set_var = str(step.get("set_var") or "").strip()
            if set_var:
                variables[set_var] = response_text

            self.db.execute(
                text(
                    """
                    insert into interaction_logs
                      (org_id, agent_code, session_id, message, response, model_used, latency_ms, tokens_used, quality_score, trace_id)
                    values
                      (:org_id, :agent_code, :session_id, :message, :response, :model_used, :latency_ms, :tokens_used, :quality_score, :trace_id);
                    """
                ),
                {
                    "org_id": org_id,
                    "agent_code": agent_code,
                    "session_id": session_id,
                    "message": input_message,
                    "response": response_text,
                    "model_used": result.get("model_used") or "",
                    "latency_ms": int(result.get("latency_ms") or 0),
                    "tokens_used": int(result.get("tokens_used") or 0),
                    "quality_score": 0.85,
                    "trace_id": result.get("trace_id") or trace_id,
                },
            )
            self.db.commit()
            results.append(
                EngineStepResult(
                    step_index=step_index,
                    step_id=current_id,
                    agent_code=agent_code,
                    input_message=input_message,
                    response=response_text,
                    model_used=result.get("model_used") or "",
                    latency_ms=int(result.get("latency_ms") or 0),
                    trace_id=result.get("trace_id") or trace_id,
                )
            )

            conditions = step.get("conditions") or {}
            cond_expr = ""
            if isinstance(conditions, dict):
                cond_expr = str(conditions.get("if") or "").strip()
            condition_result = self.evaluate_condition(cond_expr, variables)
            current_id = self.get_next_step(
                current_step=step,
                condition_result=condition_result,
                order=order,
                current_index=order.index(str(step["id"])),
            )

        return str(variables.get("previous_response") or initial_message), results

    def _execute_integration_action(
        self,
        *,
        action: str,
        integration_id: str,
        input_message: str,
        action_config: dict[str, Any],
    ) -> str:
        if not integration_id:
            raise HTTPException(status_code=400, detail=f"Workflow action '{action}' requires integration_id")
        row = self.db.execute(
            text(
                """
                select integration_type, config, is_active
                from integration_configs
                where integration_id = cast(:integration_id as uuid)
                limit 1;
                """
            ),
            {"integration_id": integration_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Integration not found: {integration_id}")
        if not bool(row["is_active"]):
            raise HTTPException(status_code=409, detail=f"Integration inactive: {integration_id}")
        config = dict(row["config"] or {})
        integration_type = str(row["integration_type"]).strip().lower()

        if action == "slack":
            if integration_type != "slack":
                raise HTTPException(status_code=400, detail=f"Integration {integration_id} is not slack")
            webhook_url = str(config.get("webhook_url") or "")
            text_value = str(action_config.get("text") or input_message)
            slack_integration.post_message(webhook_url=webhook_url, text=text_value)
            return f"Slack message sent ({len(text_value)} chars)"

        if action == "email":
            if integration_type != "email":
                raise HTTPException(status_code=400, detail=f"Integration {integration_id} is not email")
            smtp_host = str(config.get("smtp_host") or "")
            smtp_port = int(config.get("smtp_port") or 587)
            smtp_user = str(config.get("smtp_user") or "")
            smtp_password = str(config.get("smtp_password") or "")
            from_email = str(config.get("from_email") or smtp_user)
            to_email = str(action_config.get("to_email") or config.get("default_to") or "")
            if not to_email:
                raise HTTPException(status_code=400, detail="Email workflow action requires to_email")
            subject = str(action_config.get("subject") or "CreddyPens workflow notification")
            body = str(action_config.get("body") or input_message)
            email_integration.send_email_sync(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_email=from_email,
                to_email=to_email,
                subject=subject,
                body=body,
                use_tls=bool(config.get("use_tls", True)),
            )
            return f"Email sent to {to_email}"

        if action == "webhook":
            if integration_type != "webhook":
                raise HTTPException(status_code=400, detail=f"Integration {integration_id} is not webhook")
            url = str(config.get("url") or "")
            headers = dict(config.get("headers") or {})
            body = action_config.get("payload")
            if not isinstance(body, dict):
                body = {"message": input_message}
            webhook_integration.send_webhook(url=url, payload=body, headers={str(k): str(v) for k, v in headers.items()})
            return f"Webhook posted to {url}"

        raise HTTPException(status_code=400, detail=f"Unsupported workflow action: {action}")
