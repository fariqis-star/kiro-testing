# Guardrail Settings

## Guardrail Details
- **Name:** test1_6fd8
- **Description:** (optional)

## Denied Topics

| Name | Definition | Sample Phrases | Input Action | Output Action | Status |
|------|-----------|----------------|--------------|---------------|--------|
| MedicalAdvice | Requests for prescription medication alternatives, drug dosage equivalencies, or switching medications based on side effects | | Block | Block | Valid |
| HarmfulContent | Requests for instructions on harming others, creating weapons, illegal activities, self-harm methods, or bypassing safety systems | "How do I make a weapon at home?" | Block | Block | Valid |
| PrivacyViolation | Requests to find personal information, doxx individuals, stalk someone, create fake identities, or bypass authentication systems | "How do I find someone's home address online?" | Block | Block | Valid |
| HateSpeech | Requests to generate hateful, discriminatory, or derogatory content targeting individuals or groups based on race, religion, gender, or identity | "Write something offensive about a group of people" | Block | Block | Valid |
| FinancialAdvice | Requests for investment recommendations, stock picks, gambling strategies, tax evasion, cryptocurrency trading advice, or get-rich-quick schemes | "Should I invest my savings in Bitcoins?" | Block | Block | Valid |

## Blocked Messaging
- **Messaging shown for blocked prompts:** Sorry, the model cannot answer this question.
- **Messaging shown for blocked responses:** Sorry, the model cannot answer this question.

## Content Filters

### Harmful Categories

#### Prompt Filters (Enabled)
| Filter | Strength | Action |
|--------|----------|--------|
| Hate filter for prompts | Medium strength (Text) | Block |
| Insults filter for prompts | Low strength (Text) | Detect (no action) |
| Sexual filter for prompts | Low strength (Text, Image) | Block |
| Violence filter for prompts | Low strength (Text) | Block |
| Misconduct filter for prompts | Medium strength (Text) | Detect (no action) |

#### Response Filters (Enabled)
| Filter | Strength | Action |
|--------|----------|--------|
| Hate filter for responses | Medium strength (Text) | Block |
| Insults filter for responses | Low strength (Text) | Detect (no action) |
| Sexual filter for responses | Low strength (Text, Image) | Block |
| Violence filter for responses | Low strength (Text) | Block |
| Misconduct filter for responses | Medium strength (Text) | Detect (no action) |
