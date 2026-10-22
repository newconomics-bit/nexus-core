from database import get_memories_by_agent
from models import CorporateMemory


async def inject_memory(base_prompt: str, target_agent: str) -> str:
    memories = await get_memories_by_agent(target_agent)
    if not memories:
        return base_prompt

    memory_lines = []
    for memory in memories:
        memory_lines.append(f"- [{memory.category.value}] {memory.lesson_text} (Severity: {memory.severity.value})")

    memory_block = "\n\n--- CORPORATE MEMORY (LESSONS LEARNED) ---\n" + "\n".join(memory_lines)

    return base_prompt + memory_block