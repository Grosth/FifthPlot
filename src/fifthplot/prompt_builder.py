"""Construcción determinista de prompts de ilustración."""

from fifthplot.domain import Character, Scene, Story


def character_identity(character: Character) -> str:
    identity = character.visual_prompt.strip().rstrip(".")
    return f"Character identity: {identity}."


def scene_prompt(story: Story, scene: Scene) -> str:
    descriptions = [
        character_identity(character)
        for character in story.characters
        if character.name.casefold() in {name.casefold() for name in scene.characters_present}
    ]
    context = " ".join(descriptions)
    action = scene.image_prompt.strip().rstrip(".")
    setting = scene.background_prompt.strip().rstrip(".")
    style = story.visual_style.strip().rstrip(".")
    return (
        f"{style}. {context} Scene action: {action}. "
        f"Setting and lighting: {setting}. Complete storybook illustration, "
        "all visible characters integrated into the scene, coherent composition."
    )


def bounded_scene_prompt(story: Story, scene: Scene, tokenizer, max_tokens: int = 70) -> str:
    """Build a scene prompt below CLIP's limit while preserving each section."""
    present_names = {name.casefold() for name in scene.characters_present}
    characters = [
        character
        for character in story.characters
        if character.name.casefold() in present_names
    ]

    def shorten(text: str, budget: int) -> str:
        words = text.strip().split()
        while words and len(
            tokenizer(" ".join(words), add_special_tokens=False).input_ids
        ) > budget:
            words.pop()
        return " ".join(words).rstrip(".,;:")

    action = shorten(scene.image_prompt, 18)
    setting = shorten(scene.background_prompt, 6)
    style = shorten(story.visual_style, 5)
    identity_budget = 20
    if characters:
        per_character = max(3, identity_budget // len(characters))
        identities = [
            shorten(character.visual_prompt, per_character)
            for character in characters
        ]
        # Give unused tokens from short identities to the protagonist.
        used = sum(
            len(tokenizer(item, add_special_tokens=False).input_ids)
            for item in identities
        )
        if used < identity_budget:
            first = identities[0]
            first_count = len(tokenizer(first, add_special_tokens=False).input_ids)
            # Reapply the larger budget to the first character; the tokenizer
            # still keeps this within the shared identity budget.
            identities[0] = shorten(
                characters[0].visual_prompt,
                min(identity_budget - (used - first_count), identity_budget),
            )
        context = "; ".join(identities)
    else:
        context = ""

    prompt = (
        f"Action: {action}. Characters: {context}. Setting: {setting}. "
        "Watercolor storybook, soft brushstrokes. "
        f"Visual style: {style}. Complete scene illustration."
    )
    # Labels and punctuation vary by tokenization; trim setting first to retain
    # action and character identity whenever a tokenizer uses extra tokens.
    while len(tokenizer(prompt, add_special_tokens=False).input_ids) > max_tokens:
        setting_words = setting.split()
        if setting_words:
            setting = " ".join(setting_words[:-1]).rstrip(".,;:")
        elif style:
            style_words = style.split()
            style = " ".join(style_words[:-1]).rstrip(".,;:")
        elif len(action.split()) > 8:
            action = " ".join(action.split()[:-1]).rstrip(".,;:")
        else:
            break
        prompt = (
            f"Action: {action}. Characters: {context}. Setting: {setting}. "
            "Watercolor storybook, soft brushstrokes. "
            f"Visual style: {style}. Complete scene illustration."
        )
    return prompt


NEGATIVE_PROMPT = (
    "cropped, missing character, duplicate character, extra limbs, extra ears, "
    "deformed anatomy, text, watermark, photorealistic, 3d render, plastic texture"
)
