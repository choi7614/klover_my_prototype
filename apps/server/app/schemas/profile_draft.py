"""F2 전용 계약. 소유자는 요청 입력에 넣지 않는다."""

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
ShortText = Annotated[str, StringConstraints(max_length=200)]
Direction = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Section = Literal["highlights", "ongoing", "issues", "next_week"]
SECTIONS = ("highlights", "ongoing", "issues", "next_week")
Action = Literal["shorter", "politer", "rewrite"]


class F2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Profile(F2Model):
    name: Annotated[str, Field(max_length=100)] = ""
    title: ShortText = ""
    org: ShortText = ""
    duties: Annotated[str, Field(max_length=2000)] = ""
    frequent_contacts: tuple[ShortText, ...] = Field(default=(), max_length=30)
    formality: Annotated[int, Field(strict=True, ge=0, le=100)] = 70
    reply_length: Literal["short", "normal", "long"] = "normal"
    greeting: Annotated[str, Field(max_length=1000)] = ""
    closing: Annotated[str, Field(max_length=1000)] = ""
    signature: Annotated[str, Field(max_length=2000)] = ""
    style_learning_enabled: Annotated[bool, Field(strict=True)] = False
    excluded_phrases: tuple[ShortText, ...] = Field(default=(), max_length=100)
    report_sections: tuple[Section, ...] = SECTIONS
    report_recipient: ShortText = ""
    report_style: Literal["bullet", "prose"] = "bullet"

    @field_validator("report_sections")
    @classmethod
    def section_order(cls, value):
        if len(value) != 4 or set(value) != set(SECTIONS):
            raise ValueError("보고 섹션 네 개를 중복 없이 지정하세요")
        return value

    @field_validator("frequent_contacts", "excluded_phrases")
    @classmethod
    def unique_nonblank(cls, value):
        if any(not item.strip() for item in value) or len(set(value)) != len(value):
            raise ValueError("비어 있거나 중복된 항목은 사용할 수 없습니다")
        return value

    @field_validator("*", mode="after")
    @classmethod
    def no_controls(cls, value):
        texts = (value,) if isinstance(value, str) else value if isinstance(value, tuple) else ()
        if any(
            isinstance(text, str) and any(ord(c) < 32 and c not in "\n\t" for c in text)
            for text in texts
        ):
            raise ValueError("제어 문자는 사용할 수 없습니다")
        return value


class ProfileState(F2Model):
    profile: Profile = Field(default_factory=Profile)
    exists: bool = False
    version: int = 0


class ProfileUpdate(F2Model):
    profile: Profile
    expected_version: Annotated[int, Field(strict=True, ge=0)]
    consent_given: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def name_required(self) -> Self:
        if not self.profile.name.strip():
            raise ValueError("이름을 입력하세요")
        return self


class StyleState(F2Model):
    enabled: bool = False
    status: Literal["disabled", "unavailable", "ready"] = "disabled"
    analyzed_count: Annotated[int, Field(strict=True, ge=0)] = 0
    phrases: tuple[ShortText, ...] = Field(default=(), max_length=10)
    traits: tuple[ShortText, ...] = Field(default=(), max_length=20)


class PreviewRequest(F2Model):
    profile: Profile


class Evidence(F2Model):
    span: tuple[Annotated[int, Field(strict=True)], Annotated[int, Field(strict=True)]]
    source: Annotated[
        str,
        Field(
            pattern=r"^(profile\.(greeting|closing|signature|phrase)|mail:[A-Za-z0-9_-]{1,128})$"
        ),
    ]


class GeneratedDraft(F2Model):
    body: Annotated[str, Field(min_length=1, max_length=20000)]
    directions: tuple[Direction, ...] = Field(min_length=2, max_length=3)
    selected_direction: Direction
    evidence: tuple[Evidence, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def valid_directions(self) -> Self:
        if (
            len(set(self.directions)) != len(self.directions)
            or any(not value.strip() for value in self.directions)
            or self.selected_direction not in self.directions
            or not self.body.strip()
        ):
            raise ValueError("답장 방향 또는 본문을 확인하세요")
        return self


class DraftCreate(F2Model):
    mail_id: Identifier
    direction: Direction | None = None


class DraftSave(F2Model):
    body: Annotated[str, Field(max_length=25000)]
    expected_version: Annotated[int, Field(strict=True, ge=1)]


class DraftRevise(DraftSave):
    action: Action
    direction: Direction | None = None


class DraftMail(F2Model):
    mail_id: Identifier
    subject: str
    body_text: str
    from_addr: str
    from_name: str = ""
    received_at: AwareDatetime
    analysis_status: Literal["pending", "done", "failed"] = "pending"
    action_items: tuple[str, ...] | None = None


class Reference(F2Model):
    mail_id: Identifier
    subject: str
    received_at: AwareDatetime


class ContextStatus(F2Model):
    related: Literal["unavailable", "empty", "ready"] = "unavailable"
    analysis: Literal["unavailable", "ready"] = "unavailable"


class DraftState(F2Model):
    draft_id: Identifier
    mail_id: Identifier
    directions: tuple[str, ...]
    selected_direction: str
    body: str
    evidence: tuple[Evidence, ...]
    references: tuple[Reference, ...]
    version: int
    profile_version: int
    context_status: ContextStatus


class PreviewState(F2Model):
    body: str
    evidence: tuple[Evidence, ...]


class GenerationInput(F2Model):
    original: DraftMail
    related: tuple[DraftMail, ...] = ()
    profile: Profile
    learned_phrases: tuple[str, ...] = ()
    style_traits: tuple[str, ...] = ()
    direction: str | None = None
    action: Action | None = None
    current_body: str | None = None
    purpose: Literal["draft", "preview"] = "draft"
