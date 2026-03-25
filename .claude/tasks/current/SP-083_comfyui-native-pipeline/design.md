Now let me explore the Cinematographer node and find how prompts are currently built for 2P scenes:
Now let me look at the generation_prompt.py where the BREAK-based prompt is used, and the `__init__.py` (SDClientBase):
Now let me look at how the generation pipeline calls txt2img and how it builds the payload for multi-character scenes:
Now let me look at how the compositor output flows to prompt composition (specifically `scene_mode` and the BREAK prompt path):
Let me check the `compose_scene_with_style` function to understand where the BREAK prompt is generated for multi-character:
Now let me check the `SceneGenerateRequest` schema to understand the `comfy_workflow` field:
Now I have enough understanding. Let me check how the generation flow connects scene_mode to the payload:


Now I have a comprehensive understanding of the codebase. Let me produce the design.