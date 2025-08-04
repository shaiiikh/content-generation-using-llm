from event_llm_core import generate_titles
import argparse

def main():
    parser = argparse.ArgumentParser(description="Event Title Generation Service")
    parser.add_argument('--category', required=True, help='Event category')
    parser.add_argument('--event_type', required=True, help='Event type')
    parser.add_argument('--tone', required=True, help='Tone of the event')
    parser.add_argument('--num_titles', type=int, default=3, help='Number of titles to generate (max 5)')
    parser.add_argument('--context', required=False, default=None, help='Optional context')
    
    args = parser.parse_args()
    
    errors = []
    if not args.category or args.category.strip() == "":
        errors.append("Category is required")
    if not args.event_type or args.event_type.strip() == "":
        errors.append("Event type is required")
    if not args.tone or args.tone.strip() == "":
        errors.append("Tone is required")
    
    if errors:
        print("[Title Service] Validation Errors:")
        for error in errors:
            print(f"  • {error}")
        exit(1)
    
    num_titles = max(1, min(args.num_titles, 5))
    
    print(f"[Title Service] Generating {num_titles} titles")
    print(f"[Title Service] Category: {args.category}")
    print(f"[Title Service] Event Type: {args.event_type}")
    print(f"[Title Service] Tone: {args.tone}")
    print(f"[Title Service] Context: {args.context}")
    print("-" * 50)
    
    titles, logs = generate_titles(args.category, args.event_type, args.tone, num_titles, args.context)
    
    print("[Title Service] Generation Logs:")
    for k, v in logs.items():
        print(f"  {k}: {v}")
    
    print(f"[Title Service] Generated {len(titles)} Titles:")
    for i, title in enumerate(titles, 1):
        print(f"  {i}. {title}")

if __name__ == "__main__":
    main() 