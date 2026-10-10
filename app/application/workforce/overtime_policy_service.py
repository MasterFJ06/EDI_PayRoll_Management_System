from sqlalchemy.exc import IntegrityError

from app.application.common.unit_of_work import UnitOfWork
from app.application.workforce.overtime_schemas import OvertimePolicyCreateRequest, OvertimePolicyResponse
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.workforce.overtime import OvertimePolicyVersion
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel


class OvertimePolicyService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: OvertimePolicyCreateRequest, actor_user_id: int,
               correlation_id: str | None) -> OvertimePolicyResponse:
        policy = OvertimePolicyVersion(
            version_number=request.version_number,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            non_working_multiplier=request.non_working_multiplier,
            created_by_user_id=actor_user_id,
        )
        if self.uow.overtime_policies.has_effective_date_overlap(policy.effective_from, policy.effective_to):
            raise BusinessRuleViolation("Overtime policy effective dates overlap an existing version.")
        try:
            created = self.uow.overtime_policies.add(policy)
            self.uow.audit_events.add(
                AuditEventModel(actor_user_id=actor_user_id, action_type="OVERTIME_POLICY_CREATED",
                                resource_type="OVERTIME_POLICY_VERSION", resource_id=created.policy_id,
                                correlation_id=correlation_id),
                [
                    AuditEventChangeModel(field_name="version_number", old_value=None,
                                          new_value=str(created.version_number)),
                    AuditEventChangeModel(field_name="effective_period", old_value=None,
                                          new_value=f"{created.effective_from}..{created.effective_to or 'open'}"),
                    AuditEventChangeModel(field_name="non_working_multiplier", old_value=None,
                                          new_value=str(created.non_working_multiplier)),
                ],
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation("Overtime policy version identity conflicts with an existing version.") from exc
        return self._response(created)

    def get(self, policy_id: int) -> OvertimePolicyResponse | None:
        policy = self.uow.overtime_policies.get_by_id(policy_id)
        return self._response(policy) if policy is not None else None

    @staticmethod
    def _response(policy: OvertimePolicyVersion) -> OvertimePolicyResponse:
        if policy.policy_id is None:
            raise RuntimeError("Persisted overtime policy has no identifier.")
        return OvertimePolicyResponse(
            workforce_overtime_policy_version_id=policy.policy_id,
            version_number=policy.version_number,
            effective_from=policy.effective_from,
            effective_to=policy.effective_to,
            non_working_multiplier=policy.non_working_multiplier,
            created_by_user_id=policy.created_by_user_id,
        )
