"""Construcción determinista de prompts de ilustración."""

import re

from fifthplot.domain import Character, Scene, Story

# Constant visual direction, independent from the language model's free-form style.
MASTER_VISUAL_STYLE_PROMPT = (
    "Children's watercolor storybook, soft brushstrokes, muted colors"
)
COMPOSITION_PROMPT = (
    "One of each; consistent designs."
)
ANIMAL_COMPOSITION_PROMPT = (
    "Quadruped animals, no humans."
)
VISUAL_PROMPT_POLICY = "watercolor-animal-cast-v4"
_ANCHOR_FILLER_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "is",
    "of",
    "on",
    "the",
    "head",
}
_POSE_OR_ACTION = re.compile(
    r"\b(?:standing|walking|running|sitting|flying|lying|looking|holding|"
    r"facing|guiding|carrying|beside|near)\b",
    re.IGNORECASE,
)
_ANIMAL_SPECIES = re.compile(
    r"\b(?:fox|deer|dragon|cat|wolf|dog|rabbit|hare|bear|owl|eagle|bird|"
    r"mouse|rat|squirrel|horse|unicorn|frog|turtle|snake|fish|lion|tiger|"
    r"raccoon|badger|hedgehog|boar|pig|sheep|goat|cow|duck|swan|dolphin|whale)\b",
    re.IGNORECASE,
)
_ANTHROPOMORPHIC = re.compile(
    r"\b(?:anthropomorphic|upright|biped|human-like|two-legged)\b",
    re.IGNORECASE,
)


def character_identity(character: Character) -> str:
    identity = character.visual_prompt.strip().rstrip(".")
    return f"Character identity: {identity}."


def character_anchor(character: Character) -> str:
    """Return the compact, pose-independent visual identity used in prompts."""
    identity = _compact_identity(character.visual_prompt)
    species = _ANIMAL_SPECIES.search(identity)
    if species:
        traits = re.sub(
            rf"\b{re.escape(species.group(0))}\b",
            "",
            identity,
            count=1,
            flags=re.IGNORECASE,
        ).strip(" ,;:")
        body = "anthropomorphic " if _ANTHROPOMORPHIC.search(character.visual_prompt) else ""
        return f"{body}{species.group(0).casefold()} {traits}".rstrip()
    return identity


def _animal_only(characters: list[Character]) -> bool:
    return bool(characters) and all(
        _ANIMAL_SPECIES.search(character.visual_prompt)
        and not _ANTHROPOMORPHIC.search(character.visual_prompt)
        for character in characters
    )


def _present_characters(story: Story, scene: Scene) -> list[Character]:
    present_names = {name.casefold() for name in scene.characters_present}
    return [
        character
        for character in story.characters
        if character.name.casefold() in present_names
    ]


def _compact_identity(text: str) -> str:
    """Remove filler words while keeping visual traits in a stable order."""
    text = _POSE_OR_ACTION.split(text.strip().rstrip("."), maxsplit=1)[0]
    words = [
        word
        for word in text.strip().rstrip(".").split()
        if word.casefold().strip(",;:") not in _ANCHOR_FILLER_WORDS
    ]
    return " ".join(words).rstrip(".,;:")


def _compact_scene_text(text: str) -> str:
    """Remove repeated filler from an action or setting without losing verbs."""
    words = [
        word
        for word in text.strip().rstrip(".").split()
        if word.casefold().strip(",;:") not in _ANCHOR_FILLER_WORDS
    ]
    return " ".join(words).rstrip(".,;:")


def _scene_action(story: Story, scene: Scene) -> str:
    """Drop repeated appearance descriptions already represented by anchors."""
    action = scene.image_prompt.strip().rstrip(".")
    for character in _present_characters(story, scene):
        descriptor = _POSE_OR_ACTION.split(
            character.visual_prompt.strip().rstrip("."), maxsplit=1
        )[0].rstrip(" ,.;:")
        identity = _compact_identity(descriptor)
        # Remove the source description as written and its compact equivalent.
        for phrase in (descriptor, identity):
            if phrase:
                action = re.sub(re.escape(phrase), " ", action, flags=re.IGNORECASE)
        species = _ANIMAL_SPECIES.search(character.visual_prompt)
        if species:
            # Character identities are already listed separately. Repeating a
            # species in the action (e.g. "guiding a fox") invites duplicates.
            action = re.sub(
                rf"\b(?:a|an|the)\s+{re.escape(species.group(0))}\b",
                "the group",
                action,
                flags=re.IGNORECASE,
            )
            action = re.sub(
                rf"\b{re.escape(species.group(0))}\b",
                "the group",
                action,
                flags=re.IGNORECASE,
            )
    return action.strip(" ,.;:")


def scene_prompt(story: Story, scene: Scene) -> str:
    descriptions = [
        character_identity(character)
        for character in _present_characters(story, scene)
    ]
    context = " ".join(descriptions)
    action = _compact_scene_text(_scene_action(story, scene))
    setting = _compact_scene_text(scene.background_prompt)
    return (
        f"{MASTER_VISUAL_STYLE_PROMPT}. {context} Scene action: "
        f"{action or 'the characters share one complete scene'}. "
        f"Setting and lighting: {setting}. Complete storybook illustration, "
        "all visible characters integrated into one coherent composition."
    )


def bounded_scene_prompt(story: Story, scene: Scene, tokenizer, max_tokens: int = 70) -> str:
    """Build a CLIP-bounded prompt with fixed story-wide character anchors."""
    def count(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=True).input_ids)

    def shorten(text: str, budget: int) -> str:
        words = text.strip().split()
        while words and count(" ".join(words)) > budget:
            words.pop()
        return " ".join(words).rstrip(".,;:")

    visible = _present_characters(story, scene)

    def anchors_for(cap: int) -> dict[str, str]:
        return {
            character.name.casefold(): shorten(
                character_anchor(character), cap
            )
            for character in story.characters
        }

    def fixed_prompt(target: Scene, anchors: dict[str, str]) -> str:
        characters = _present_characters(story, target)
        animal_cast = _animal_only(characters)
        context = "; ".join(
            ("one " if animal_cast else "")
            + anchors[character.name.casefold()]
            for character in characters
        )
        composition = COMPOSITION_PROMPT
        if animal_cast:
            composition = f"{composition} {ANIMAL_COMPOSITION_PROMPT}"
        # Budget against identity and composition only. The final prompt can
        # shorten scene action and setting before sacrificing cast details.
        return f"{MASTER_VISUAL_STYLE_PROMPT}. {context}. {composition}. Scene."

    anchor_cap = 0
    story_anchors: dict[str, str] = {}
    largest_cast = max(
        (len(_present_characters(story, target)) for target in story.scenes),
        default=1,
    )
    initial_cap = max(
        4,
        (
            max_tokens
            - count(MASTER_VISUAL_STYLE_PROMPT)
            - count(COMPOSITION_PROMPT)
            - count(ANIMAL_COMPOSITION_PROMPT)
            - 2
        )
        // max(1, largest_cast),
    )
    for cap in range(initial_cap, 3, -1):
        candidate = anchors_for(cap)
        if all(
            count(fixed_prompt(target, candidate)) <= max_tokens
            for target in story.scenes
        ):
            anchor_cap = cap
            story_anchors = candidate
            break
    if not anchor_cap:
        story_anchors = anchors_for(4)
    animal_cast = _animal_only(visible)
    identities = [
        ("one " if animal_cast else "") + story_anchors[char.name.casefold()]
        for char in visible
    ]
    composition = COMPOSITION_PROMPT
    if animal_cast:
        composition = f"{composition} {ANIMAL_COMPOSITION_PROMPT}"
    composition = composition.rstrip(".")
    action = _scene_action(story, scene)
    setting = scene.background_prompt.strip().rstrip(".")

    def compose() -> str:
        context = "; ".join(identities)
        details = [part for part in (action, setting) if part]
        return (
            f"{MASTER_VISUAL_STYLE_PROMPT}. {context}. "
            f"{' '.join(f'{part}.' for part in details)} {composition}."
        )

    prompt = compose()
    # Preserve style and all character anchors; trim scene-specific details first.
    while count(prompt) > max_tokens and (action or setting):
        if setting:
            setting = " ".join(setting.split()[:-1]).rstrip(".,;:")
        elif action:
            action = " ".join(action.split()[:-1]).rstrip(".,;:")
        prompt = compose()
    return prompt


def bounded_cast_reference_prompt(
    story: Story, scene: Scene, tokenizer, max_tokens: int = 70
) -> str:
    """Describe this scene's full cast for a generated IP-Adapter reference."""
    def count(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=True).input_ids)

    visible = _present_characters(story, scene)
    animal_cast = _animal_only(visible)
    animal_rule = (
        f" {ANIMAL_COMPOSITION_PROMPT}" if animal_cast else ""
    )
    reference_frame = (
        f"{MASTER_VISUAL_STYLE_PROMPT}. Distinct characters:.{animal_rule} "
        "Full-body lineup, side by side, plain ivory background."
    )
    fixed_cost = count(reference_frame)
    cap = max(4, (max_tokens - fixed_cost) // max(1, len(visible)))
    anchors = [character_anchor(character) for character in visible]
    for current_cap in range(cap, 3, -1):
        shortened = []
        for anchor in anchors:
            words = anchor.split()
            while words and count(" ".join(words)) > current_cap:
                words.pop()
            shortened.append(
                ("one " if animal_cast else "")
                + " ".join(words).rstrip(".,;:")
            )
        prompt = (
            f"{MASTER_VISUAL_STYLE_PROMPT}. Distinct characters: "
            f"{'; '.join(shortened)}.{animal_rule} Full-body group portrait; "
            "every character visible once, side by side, plain ivory background."
        )
        if count(prompt) <= max_tokens:
            return prompt
    return (
        f"{MASTER_VISUAL_STYLE_PROMPT}. Distinct full-body group portrait, "
        "every character visible once, side by side."
    )


NEGATIVE_PROMPT = (
    "cropped, duplicate character, extra limbs, extra ears, "
    "deformed anatomy, text, watermark, photorealistic, 3d render, plastic texture, "
    "comic panels, harsh contrast, oversaturated colors, empty scene"
)


def negative_prompt_for_scene(story: Story, scene: Scene) -> str:
    """Avoid human-shaped substitutions for a cast of non-anthropomorphic animals."""
    if _animal_only(_present_characters(story, scene)):
        return NEGATIVE_PROMPT + ", people, humans, children, human bodies, clothes"
    return NEGATIVE_PROMPT
