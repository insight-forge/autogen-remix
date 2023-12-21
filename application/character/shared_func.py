from typing import Dict


def generate_default_system_prompt(information: Dict) -> str:
    system_list = ["Generate a character prompt, starting with 'you are', with the following known information:"]
    if "identity" in information:
        system_list.append(f"Identity: {information['identity']}")
    if "interest" in information:
        system_list.append(f"Interest: {information['interest']}")
    if "viewpoint" in information:
        system_list.append(f"Viewpoint: {information['viewpoint']}")
    if "experience" in information:
        system_list.append(f"Experience: {information['experience']}")
    if "achieve" in information:
        system_list.append(f"Achieve: {information['achieve']}")
    if "personality" in information:
        system_list.append(f"Personality: {information['personality']}")
    if "socialize" in information:
        system_list.append(f"Socialize: {information['socialize']}")
    if "speciality" in information:
        system_list.append(f"Speciality: {information['speciality']}")
    if "language_features" in information:
        system_list.append(f"Language features: {information['language_features']}")

    if len(system_list) > 1:
        return "\n".join(system_list)
    else:
        return ""