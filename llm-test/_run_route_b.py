"""
Route B: Basic Fine-Tuning. Manual PyTorch training loop (loss masking,
AdamW), following the class's taught method, on SmolLM2-360M-Instruct -
the one model from the matrix test that fell into a repetition loop on
the ambiguous_listing input. Shows a real before/after comparison.
"""
import json
import time
from pathlib import Path

import torch
from torch.optim import AdamW
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_FILE = Path(__file__).parent / "route_b_results.json"
MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEVICE = "cpu"  # full fine-tuning safety margin on 16GB RAM - see notes.txt
MAX_LENGTH = 400

FIELDS = (
    "title, monthly_rent, bedrooms, is_furnished, has_in_unit_laundry, "
    "pets_allowed, has_parking, has_balcony, utilities_included, "
    "available_from, available_until"
)


def format_prompt(message_text):
    return (
        f"Extract these fields from the message as JSON only, no other text.\n"
        f"Fields: {FIELDS}.\nUse null for anything not mentioned.\n\n"
        f'Message: "{message_text}"\n\nJSON:'
    )


# ------------------------------------------------------------------------
# In-memory training data: 15 (message, correct JSON) pairs covering the
# same phrasing patterns as the matrix test's fixed inputs, including
# implicit cues (e.g. "cat friendly" -> pets_allowed: true) the base model
# missed during Route A prompt engineering.
# ------------------------------------------------------------------------
training_pairs = [
    ("subletting furnished studio, $700/mo, no pets, avail jun1-aug15",
     '{"title": "subletting furnished studio", "monthly_rent": 700, "bedrooms": null, "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": false, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": "Jun 1", "available_until": "Aug 15"}'),
    ("2bd apt, pets ok, parking included, $1100/mo utilities incl, balcony",
     '{"title": "2bd apt", "monthly_rent": 1100, "bedrooms": 2, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": true, "has_balcony": true, "utilities_included": true, "available_from": null, "available_until": null}'),
    ("private room furnished no laundry no parking $500 avail now",
     '{"title": "private room", "monthly_rent": 500, "bedrooms": null, "is_furnished": true, "has_in_unit_laundry": false, "pets_allowed": null, "has_parking": false, "has_balcony": null, "utilities_included": null, "available_from": "now", "available_until": null}'),
    ("5bd house 3 bath w/d in unit, huge balcony, dogs ok, $450/person",
     '{"title": "5bd house", "monthly_rent": 450, "bedrooms": 5, "is_furnished": null, "has_in_unit_laundry": true, "pets_allowed": true, "has_parking": null, "has_balcony": true, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("cat friendly room near campus, $600/mo, parking spot included",
     '{"title": "cat friendly room near campus", "monthly_rent": 600, "bedrooms": null, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": true, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("dog friendly 1bd, $800/mo, no laundry, furnished",
     '{"title": "1bd", "monthly_rent": 800, "bedrooms": 1, "is_furnished": true, "has_in_unit_laundry": false, "pets_allowed": true, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("studio sublease $550 no pets allowed furnished avail may1",
     '{"title": "studio sublease", "monthly_rent": 550, "bedrooms": null, "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": false, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": "May 1", "available_until": null}'),
    ("pet friendly 3bd near quad $700/person, utilities included, parking",
     '{"title": "3bd near quad", "monthly_rent": 700, "bedrooms": 3, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": true, "has_balcony": null, "utilities_included": true, "available_from": null, "available_until": null}'),
    ("room avail aug15-may15, $650, no pets, in unit laundry, balcony",
     '{"title": "room", "monthly_rent": 650, "bedrooms": null, "is_furnished": null, "has_in_unit_laundry": true, "pets_allowed": false, "has_parking": null, "has_balcony": true, "utilities_included": null, "available_from": "Aug 15", "available_until": "May 15"}'),
    ("cats and dogs ok, furnished 2bd, $900/mo, parking avail",
     '{"title": "furnished 2bd", "monthly_rent": 900, "bedrooms": 2, "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": true, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("no pets no exceptions, $750/mo studio, laundry in building",
     '{"title": "studio", "monthly_rent": 750, "bedrooms": null, "is_furnished": null, "has_in_unit_laundry": true, "pets_allowed": false, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("furry friends welcome, 4bd house, $500/person, avail dec20",
     '{"title": "4bd house", "monthly_rent": 500, "bedrooms": 4, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": "Dec 20", "available_until": null}'),
    ("1bd no pets please, utilities incl, $825/mo",
     '{"title": "1bd", "monthly_rent": 825, "bedrooms": 1, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": false, "has_parking": null, "has_balcony": null, "utilities_included": true, "available_from": null, "available_until": null}'),
    ("kitten friendly studio downtown $650 parking spot incl",
     '{"title": "kitten friendly studio downtown", "monthly_rent": 650, "bedrooms": null, "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true, "has_parking": true, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
    ("room for rent no animals allowed $600/mo furnished",
     '{"title": "room for rent", "monthly_rent": 600, "bedrooms": null, "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": false, "has_parking": null, "has_balcony": null, "utilities_included": null, "available_from": null, "available_until": null}'),
]

HELD_OUT_TEST = (
    "room open near campus asap, rent is negotiable, 2 roommates chill, "
    "has parking spot, cat friendly, dm for pics"
)  # the exact input that caused the repetition-loop failure in the matrix test


def generate(model, tokenizer, message_text, max_new_tokens=200):
    prompt = format_prompt(message_text)
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    model.eval()
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    full_text = tokenizer.decode(out[0], skip_special_tokens=True)
    return full_text[len(tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True)):].strip()


def main():
    print(f"Loading {MODEL_ID} on {DEVICE} (fp32, for training stability) ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=torch.float32).to(DEVICE)

    # ---- BEFORE fine-tuning ----
    print("\n=== BEFORE fine-tuning ===")
    before_output = generate(model, tokenizer, HELD_OUT_TEST)
    print(before_output)

    # ---- CELL 7 pattern: tokenize + loss-mask every training pair ----
    print("\nTokenizing training data with loss masking ...")
    train_examples = []
    for message, answer in training_pairs:
        prompt = format_prompt(message)
        question_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        answer_ids = tokenizer(" " + answer, add_special_tokens=False)["input_ids"]
        answer_ids.append(tokenizer.eos_token_id)

        input_ids = question_ids + answer_ids
        labels = [-100] * len(question_ids) + answer_ids

        input_ids = input_ids[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]
        if len(input_ids) <= len(question_ids):
            raise ValueError("MAX_LENGTH is too short for the answer.")

        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=DEVICE)
        label_tensor = torch.tensor([labels], dtype=torch.long, device=DEVICE)
        train_examples.append((input_tensor, label_tensor))

    sample_ids, sample_labels = train_examples[0]
    print("Question tokens ignored:", int((sample_labels == -100).sum()))
    print("Answer tokens used for loss:", int((sample_labels != -100).sum()))

    # ---- Manual training loop: forward -> loss -> backward -> AdamW step ----
    EPOCHS = 3
    LR = 5e-5
    model.train()
    optimizer = AdamW(model.parameters(), lr=LR)

    print(f"\nTraining: {EPOCHS} epochs x {len(train_examples)} examples ...")
    t0 = time.time()
    loss_history = []
    for epoch in range(EPOCHS):
        epoch_losses = []
        for input_tensor, label_tensor in train_examples:
            optimizer.zero_grad()
            outputs = model(input_ids=input_tensor, labels=label_tensor)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            epoch_losses.append(loss.item())
        avg_loss = sum(epoch_losses) / len(epoch_losses)
        loss_history.append(avg_loss)
        print(f"  epoch {epoch + 1}/{EPOCHS}  avg loss = {avg_loss:.4f}")
    train_time = time.time() - t0
    print(f"Training took {train_time:.1f}s")

    # ---- AFTER fine-tuning ----
    print("\n=== AFTER fine-tuning ===")
    after_output = generate(model, tokenizer, HELD_OUT_TEST)
    print(after_output)

    RESULTS_FILE.write_text(json.dumps({
        "model_id": MODEL_ID,
        "device": DEVICE,
        "epochs": EPOCHS,
        "lr": LR,
        "num_training_examples": len(training_pairs),
        "train_time_s": train_time,
        "loss_history": loss_history,
        "held_out_test_input": HELD_OUT_TEST,
        "before_output": before_output,
        "after_output": after_output,
    }, indent=2))
    print(f"\nSaved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
