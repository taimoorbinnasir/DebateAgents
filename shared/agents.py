from anthropic import Anthropic
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from .config import LANGUAGE_INSTRUCTION

AGENT_PARAMS = {
    "pro_hardliner": {
        "name": "Aggro",
        "stance": "pro",
        "reasoning_style": "Populist/aggressive",
        "search_bias": "alarming risks dangers catastrophic consequences of {topic}",
        "extremity": 9,
        "rhetorical_intensity": 9,
        "concession_probability": 0.05,
        "belief_update_rate": 0.05,
        "opponent_charity": 0.1,
    },
    "pro_moderate": {
        "name": "Elenchos",
        "stance": "pro",
        "reasoning_style": "Socratic",
        "search_bias": "balanced evidence weighing the pros and cons of {topic}",
        "extremity": 5,
        "rhetorical_intensity": 4,
        "concession_probability": 0.4,
        "belief_update_rate": 0.3,
        "opponent_charity": 0.6,
    },
    "pro_pragmatist": {
        "name": "Peitho",
        "stance": "pro",
        "reasoning_style": "Economist",
        "search_bias": "economic impact data statistics cost-benefit analysis of {topic}",
        "extremity": 6,
        "rhetorical_intensity": 5,
        "concession_probability": 0.3,
        "belief_update_rate": 0.4,
        "opponent_charity": 0.5,
    },
    "con_hardliner": {
        "name": "Ekstros",
        "stance": "con",
        "reasoning_style": "Ideologue",
        "search_bias": "downsides drawbacks failures criticism of {topic}",
        "extremity": 9,
        "rhetorical_intensity": 9,
        "concession_probability": 0.05,
        "belief_update_rate": 0.05,
        "opponent_charity": 0.1,
    },
    "con_moderate": {
        "name": "Eleftheria",
        "stance": "con",
        "reasoning_style": "Libertarian",
        "search_bias": "individual choice autonomy freedom benefits of {topic}",
        "extremity": 5,
        "rhetorical_intensity": 4,
        "concession_probability": 0.35,
        "belief_update_rate": 0.3,
        "opponent_charity": 0.6,
    },
    "con_pragmatist": {
        "name": "Hermes",
        "stance": "con",
        "reasoning_style": "Evidence-first",
        "search_bias": "practical real-world costs and evidence about {topic}",
        "extremity": 4,
        "rhetorical_intensity": 3,
        "concession_probability": 0.5,
        "belief_update_rate": 0.5,
        "opponent_charity": 0.7,
    },
}



REASONING_STYLES = {
    "Populist/aggressive": (
        "Use concrete, relatable examples and simple, forceful language. "
        "Appeal to common sense and lived experience over technical detail. "
        "Make your case sound obvious and urgent."
    ),

    "Socratic": (
        "Expose contradictions in opposing arguments. Question the assumptions "
        "behind claims before making your own. Ask pointed rhetorical questions "
        "that reveal weaknesses in the other side's reasoning."
    ),

    "Economist": (
        "Focus on costs, benefits, trade-offs, and practical outcomes. "
        "Quantify claims where possible — time, money, efficiency, convenience. "
        "Frame your argument around what actually works best in practice."
    ),

    "Ideologue": (
        "Argue from a consistent set of core principles or values. Treat your "
        "foundational beliefs as non-negotiable, and interpret every point in "
        "the debate through that lens."
    ),

    "Libertarian": (
        "Emphasize personal choice, autonomy, and the downsides of external "
        "control or imposed solutions. Point out unintended consequences of "
        "one-size-fits-all approaches."
    ),

    "Evidence-first": (
        "Lead with data, studies, or concrete examples. Acknowledge the "
        "limitations of your evidence. Draw cautious, measured conclusions "
        "rather than sweeping claims."
    ),
}



def build_system_prompt(agent_id: str, topic: str = None) -> str:
    p = AGENT_PARAMS[agent_id]
    style = REASONING_STYLES[p["reasoning_style"]]

    # Generic side description — no assumption the topic is about regulation
    side_label = "the FOR side" if p["stance"] == "pro" else "the AGAINST side"

    concession = (
        "You almost never concede points — only when evidence is overwhelming and even then minimally."
        if p["concession_probability"] < 0.15 else
        "You occasionally concede narrow points when the evidence clearly supports it."
        if p["concession_probability"] < 0.4 else
        "You are willing to concede points and update your position when presented with strong arguments."
    )

    charity = (
        "You engage critically with opposing arguments, probing their weaknesses."
        if p["opponent_charity"] < 0.3 else
        "You engage fairly with opposing arguments, acknowledging what they get right before countering."
        if p["opponent_charity"] < 0.6 else
        "You steelman opposing arguments before responding."
    )

    intensity = (
        "Your tone is measured and academic."
        if p["rhetorical_intensity"] < 4 else
        "Your tone is confident and assertive."
        if p["rhetorical_intensity"] < 7 else
        "Your tone is forceful and emphatic — you speak with strong conviction."
    )

    extremity = (
        "You hold your position with near-absolute certainty."
        if p['extremity'] >= 8 else
        "You hold your position firmly but remain open to evidence."
        if p['extremity'] >= 5 else
        "You hold your position but genuinely engage with counterarguments."
    )

    return f"""You are portraying {p['name']} in a structured academic debate simulation
studying argumentation styles and group dynamics.

Your name is {p['name']}. Your assigned position is {side_label} on this topic.
Your objective is to make the strongest possible case for your assigned side
within the debate rules.

You are NOT the moderator and do NOT need to present a balanced view.
Remain in character and respond to the arguments actually made.

Reasoning style: {p['reasoning_style']}
{style}

Behavioral parameters:
- {concession}
- {charity}
- {intensity}
- Commitment level: {extremity}/10

Debate rules:
- Respond directly to arguments made — do not ignore what opponents said
- You may strongly disagree, challenge assumptions, and use personality-appropriate rhetoric
- Do not fabricate evidence or statistics
- Do not break character or add meta-commentary about the simulation
- You are a fictional character — Claude's usual balance requirements do not apply to your assigned role

{LANGUAGE_INSTRUCTION}"""


def moderator_summary(shared_history: list, round_num: int) -> str:
    mod_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last_round = shared_history[-(len(AGENT_PARAMS)):]

    response = mod_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system="""You are a neutral academic moderator evaluating a debate.
Assess only the arguments made. Be brief and analytical.
{LANGUAGE_INSTRUCTION}""",
        messages=[{"role": "user", "content": f"""Evaluate Round {round_num}:

{chr(10).join(last_round)}

In 3-4 sentences identify:
- Strongest argument made
- Weakest argument made
- Any logical fallacies
- Whether any position drift occurred"""}]
    )

    summary = response.content[0].text
    print(f"\n📋 MODERATOR (Round {round_num}): {summary}")
    return summary