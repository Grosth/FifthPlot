"""Modelos y reglas de dominio de FifthPlot."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NonEmptyText = Annotated[str, Field(min_length=1)]
SceneNumber = Literal[1, 2, 3, 4, 5]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Character(StrictModel):
    name: NonEmptyText
    description: NonEmptyText
    role: NonEmptyText
    visual_prompt: NonEmptyText


class Scene(StrictModel):
    number: SceneNumber
    scene_title: NonEmptyText
    narrative: NonEmptyText
    image_prompt: NonEmptyText
    background_prompt: NonEmptyText
    characters_present: list[NonEmptyText] = Field(
        description=(
            "Solo nombres exactos de characters[].name. No incluyas objetos, "
            "alias, traducciones ni entidades que no estén en el reparto."
        )
    )
    ambience_prompt: NonEmptyText
    voice_direction: NonEmptyText


class Story(StrictModel):
    title: NonEmptyText
    genre: NonEmptyText
    synopsis: NonEmptyText
    visual_style: NonEmptyText
    characters: list[Character] = Field(min_length=1, max_length=4)
    scenes: list[Scene] = Field(min_length=5, max_length=5)

    @field_validator("title", "genre", "synopsis", "visual_style")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El texto no puede estar vacío.")
        return value

    @model_validator(mode="after")
    def validate_scene_sequence_and_cast(self) -> "Story":
        numbers = [scene.number for scene in self.scenes]
        if numbers != [1, 2, 3, 4, 5]:
            raise ValueError("El cuento debe tener las escenas 1, 2, 3, 4 y 5 en orden.")

        names = [character.name.casefold() for character in self.characters]
        if len(names) != len(set(names)):
            raise ValueError("El reparto contiene nombres repetidos.")

        cast = {character.name.casefold() for character in self.characters}
        for scene in self.scenes:
            for name in scene.characters_present:
                if name.casefold() not in cast:
                    raise ValueError(
                        f"El personaje '{name}' de la escena {scene.number} "
                        "no aparece en el reparto."
                    )
        return self


class StoryRequest(StrictModel):
    idea: NonEmptyText
    genre: NonEmptyText

    @field_validator("idea", "genre")
    @classmethod
    def require_nonblank_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La idea y el género son obligatorios.")
        return value
