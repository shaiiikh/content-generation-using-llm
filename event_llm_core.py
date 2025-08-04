import json
import os
import time
import hashlib
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv
from difflib import get_close_matches
import streamlit as st
from openai import OpenAI
import random

load_dotenv()

class SmartCache:
    def __init__(self, cache_dir="cache", ttl_hours=48):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.memory_cache = {}
        self.max_memory_items = 100
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_cache_key(self, *args, **kwargs):
        content = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get(self, key):
        if key in self.memory_cache:
            data = self.memory_cache[key]
            if datetime.now() - data['timestamp'] < self.ttl:
                return data['content']
            else:
                del self.memory_cache[key]
        
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if datetime.now() - data['timestamp'] < self.ttl:
                    if len(self.memory_cache) < self.max_memory_items:
                        self.memory_cache[key] = data
                    return data['content']
                else:
                    os.remove(cache_file)
            except:
                pass
        return None
    
    def set(self, key, content):
        data = {
            'content': content,
            'timestamp': datetime.now()
        }
        
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k]['timestamp'])
            del self.memory_cache[oldest_key]
        
        self.memory_cache[key] = data
        
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass

class PromptOptimizer:
    @staticmethod
    def compress_prompt(prompt, target_reduction=0.3):
        lines = prompt.split('\n')
        essential_lines = []
        for line in lines:
            if any(keyword in line.upper() for keyword in ['CRITICAL', 'MUST', 'REQUIRED', 'ESSENTIAL']):
                essential_lines.append(line)
            elif len(line.strip()) > 10 and not line.strip().startswith('-'):
                essential_lines.append(line[:int(len(line) * (1 - target_reduction))])
        return '\n'.join(essential_lines)
    
    @staticmethod
    def optimize_for_cost(prompt, cost_mode):
        if cost_mode == "economy":
            compressed = PromptOptimizer.compress_prompt(prompt, 0.5)
            return compressed.replace("Please provide", "Provide").replace("You should", "").replace("It is important to", "").replace("Make sure to", "")
        elif cost_mode == "premium":
            return prompt
        else:
            return PromptOptimizer.compress_prompt(prompt, 0.25)

class BatchProcessor:
    @staticmethod
    def can_batch(requests):
        return len(requests) > 1 and all(req.get('model') == requests[0].get('model') for req in requests)
    
    @staticmethod
    def create_batch_prompt(requests):
        batch_prompt = "Generate the following items in JSON format:\n"
        for i, req in enumerate(requests):
            batch_prompt += f"{i+1}. {req['type']}: {req['prompt']}\n"
        batch_prompt += "\nReturn as JSON array with 'type', 'content', and 'index' fields."
        return batch_prompt

class PerformanceAnalytics:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'avg_response_time': 0.0,
            'error_rate': 0.0
        }
    
    def record_request(self, cost, tokens, response_time, from_cache=False, error=False):
        self.metrics['total_requests'] += 1
        if from_cache:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['total_cost'] += cost
            self.metrics['total_tokens'] += tokens
        
        current_avg = self.metrics['avg_response_time']
        self.metrics['avg_response_time'] = (current_avg * (self.metrics['total_requests'] - 1) + response_time) / self.metrics['total_requests']
        
        if error:
            self.metrics['error_rate'] = (self.metrics['error_rate'] * (self.metrics['total_requests'] - 1) + 1) / self.metrics['total_requests']
    
    def get_efficiency_score(self):
        if self.metrics['total_requests'] == 0:
            return 0
        
        cache_efficiency = min(self.metrics['cache_hits'] / self.metrics['total_requests'], 1.0)
        
        avg_cost_per_request = self.metrics['total_cost'] / self.metrics['total_requests'] if self.metrics['total_requests'] > 0 else 0
        cost_efficiency = max(0, 1 - min(avg_cost_per_request / 0.005, 1))
        
        speed_efficiency = max(0, 1 - min(self.metrics['avg_response_time'] / 15, 1))
        
        error_efficiency = 1 - self.metrics['error_rate']
        
        token_efficiency = max(0, 1 - min((self.metrics['total_tokens'] / self.metrics['total_requests']) / 2000, 1)) if self.metrics['total_requests'] > 0 else 0
        
        weights = [0.25, 0.20, 0.25, 0.20, 0.10]
        components = [cache_efficiency, cost_efficiency, speed_efficiency, error_efficiency, token_efficiency]
        
        return sum(w * c for w, c in zip(weights, components)) * 100

cache = SmartCache()
analytics = PerformanceAnalytics()

def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and 'st' in globals():
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except:
            pass
    return api_key

API_KEY = get_api_key()

if not API_KEY:
    if 'st' in globals():
        st.error("OpenAI API key not found! Please add OPENAI_API_KEY to your Streamlit secrets.")
        st.stop()
    else:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add to Streamlit secrets.")

client = OpenAI(api_key=API_KEY)

def clean_json_output(raw):
    raw = raw.strip()
    if raw.startswith('```json'):
        raw = raw[len('```json'):].strip()
    if raw.startswith('```'):
        raw = raw[len('```'):].strip()
    if raw.endswith('```'):
        raw = raw[:-3].strip()
    return raw

def estimate_cost(prompt_tokens, completion_tokens, model="gpt-3.5-turbo"):
    costs = {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4": {"input": 0.03, "output": 0.06}
    }
    
    if model in costs and "input" in costs[model]:
        input_cost = costs[model]["input"] * (prompt_tokens / 1000)
        output_cost = costs[model]["output"] * (completion_tokens / 1000)
        return input_cost + output_cost
    return 0.02

def count_tokens(text):
    return max(len(text.split()), int(len(text) / 3.5))

def fuzzy_correct(user_input, valid_options):
    matches = get_close_matches(user_input, valid_options, n=1, cutoff=0.75)
    if matches:
        return matches[0]
    return user_input

def smart_api_call(system_msg, user_msg, max_tokens, temperature, model="gpt-3.5-turbo", cost_mode="balanced"):
    start_time = time.time()
    
    optimized_system = PromptOptimizer.optimize_for_cost(system_msg, cost_mode)
    optimized_user = PromptOptimizer.optimize_for_cost(user_msg, cost_mode)
    
    cache_key = cache._get_cache_key(optimized_system, optimized_user, max_tokens, temperature, model)
    cached_result = cache.get(cache_key)
    
    if cached_result:
        analytics.record_request(0, 0, time.time() - start_time, from_cache=True)
        return cached_result
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": optimized_system},
                    {"role": "user", "content": optimized_user}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.6,
                presence_penalty=0.4
            )
            
            result = response.choices[0].message.content.strip()
            cache.set(cache_key, result)
            
            prompt_tokens = count_tokens(optimized_system + optimized_user)
            completion_tokens = count_tokens(result)
            cost = estimate_cost(prompt_tokens, completion_tokens, model)
            
            analytics.record_request(cost, prompt_tokens + completion_tokens, time.time() - start_time)
            return result
            
        except Exception as e:
            if attempt == max_retries - 1:
                analytics.record_request(0, 0, time.time() - start_time, error=True)
                raise e
            time.sleep(2 ** attempt)

def get_title_examples(category, event_type, tone):
    examples = {
        ("Technology", "Conference", "Professional"): ["Tech Leadership Summit", "Digital Innovation Forum", "Future Systems Expo"],
        ("Technology", "Workshop", "Creative"): ["Code & Create Lab", "Innovation Studio", "Digital Makers Hub"],
        ("Business", "Conference", "Professional"): ["Business Growth Summit", "Leadership Excellence Forum", "Strategic Success Conference"],
        ("Business", "Seminar", "Formal"): ["Executive Mastery Series", "Strategic Leadership Institute", "Business Excellence Summit"],
        ("Education", "Conference", "Innovative"): ["Learning Revolution Summit", "Educational Innovation Forum", "Teaching Excellence Expo"]
    }
    key = (category, event_type, tone)
    if key in examples:
        return examples[key]
    return [f"{category} Excellence Summit", f"{event_type} Innovation Forum", f"Advanced {category} Workshop"]

def validate_inputs(category, event_type, tone, num_titles=3, context=None):
    errors = []
    warnings = []
    if not category or category == "Select event category":
        errors.append("Category is required")
    if not event_type or event_type == "Select event type":
        errors.append("Event type is required")
    if not tone or tone == "Select tone of event":
        errors.append("Tone is required")
    if num_titles < 1 or num_titles > 5:
        warnings.append(f"Number of titles ({num_titles}) should be between 1-5")
    if context and len(context) > 200:
        warnings.append("Context is very long - may increase costs")
    return errors, warnings

def generate_titles(category, event_type, tone, num_titles=5, context=None, cost_mode="balanced"):
    errors, warnings = validate_inputs(category, event_type, tone, num_titles, context)
    if errors:
        return [], {"errors": errors, "warnings": warnings}
    
    num_titles = max(1, min(int(num_titles), 5))
    diversity_instruction = "Each title must be unique, creative, and use different wording. Avoid repeating phrases or structures. No emojis or decorative symbols."
    
    # Enhanced context handling
    context_str = ""
    if context and context.strip():
        context_str = f"\n\nCRITICAL CONTEXT REQUIREMENTS:\n- Incorporate the following specific context: {context.strip()}\n- Ensure titles reflect the unique aspects mentioned in the context\n- Use context details to create more targeted and relevant titles\n- Make titles specific to the context provided\n- Avoid generic titles that don't reflect the context"
    
    if cost_mode == "economy":
        system_msg = f"Generate {num_titles} creative, unique {tone.lower()} event titles for {category} {event_type}. 3-6 words each, no colons. JSON format. {diversity_instruction}{context_str}"
        user_msg = f"Create {num_titles} unique, creative titles for {category} {event_type} ({tone}){context_str}"
        max_tokens = 15 * num_titles + 40
        temperature = 0.85
    elif cost_mode == "premium":
        examples = get_title_examples(category, event_type, tone)
        example_block = "\n".join([
            "[\"Innovate Now Summit\", \"Future Leaders Forum\", \"Tech Vision Expo\"]",
            "[\"Business Growth Bootcamp\", \"Leadership Mastery Workshop\", \"Strategic Success Seminar\"]",
            "[\"Learning Revolution Conference\", \"Education Innovation Forum\", \"Teaching Excellence Expo\"]"
        ])
        system_msg = f"""Expert event marketer. Generate EXACTLY {num_titles} compelling {tone.lower()} titles for {category} {event_type}.

CRITICAL REQUIREMENTS:
- Generate EXACTLY {num_titles} titles, no more, no less
- Each title must be 3-6 words long
- Each title must be unique and creative
- Use different words, phrases, and focus areas for each title
- Format as a clean JSON array: ["Title 1", "Title 2", "Title 3"]
- NO explanations, NO extra text, just the JSON array

Examples of diverse titles:
{example_block}

Style: {tone.lower()}, memorable, actionable{context_str}"""
        user_msg = f"Generate EXACTLY {num_titles} exceptional, unique titles for {category} {event_type} with {tone} tone. Return only a JSON array.{context_str}"
        max_tokens = 20 * num_titles + 60
        temperature = 0.9
    else:
        examples = get_title_examples(category, event_type, tone)
        system_msg = f"""Professional event title generator. Create EXACTLY {num_titles} {tone.lower()} titles for {category} {event_type}.

REQUIREMENTS:
- Generate EXACTLY {num_titles} titles
- Length: 3-6 words each
- Style: {tone.lower()}, memorable
- Format: JSON array only
- Each title must be unique and use different words or focus
- Avoid repeating phrases or structures

Examples: {examples[0]}, {examples[1]}{context_str}"""
        user_msg = f"Generate EXACTLY {num_titles} unique titles: {category} {event_type} ({tone}). Return JSON array only.{context_str}"
        max_tokens = 18 * num_titles + 50
        temperature = 0.85
    
    start = time.time()
    
    result = smart_api_call(system_msg, user_msg, max_tokens, temperature, cost_mode=cost_mode)
    cleaned = clean_json_output(result)
    titles = []
    parsing_error = None
    
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            titles = [str(t).strip() for t in parsed if isinstance(t, str) and t.strip()]
            titles = [t for t in titles if 3 <= len(t.split()) <= 6]
        else:
            parsing_error = "JSON is not a list"
    except Exception as e:
        parsing_error = str(e)
        lines = result.replace('[', '').replace(']', '').replace('"', '').split(',')
        for line in lines:
            clean = line.strip().strip('"').strip("'").strip('-').strip('1234567890.').strip()
            if clean and 3 <= len(clean.split()) <= 6 and clean not in titles:
                titles.append(clean)
                if len(titles) >= num_titles:
                    break
    
    seen = set()
    unique_titles = []
    for t in titles:
        if t.lower() not in seen:
            unique_titles.append(t)
            seen.add(t.lower())
    titles = unique_titles[:num_titles]
    
    retry_count = 0
    max_retries = 2 if cost_mode == "premium" else 1
    
    while len(titles) < num_titles and retry_count < max_retries:
        retry_count += 1
        needed = num_titles - len(titles)
        
        retry_system = system_msg.replace(f"EXACTLY {num_titles}", f"EXACTLY {needed} additional")
        retry_user = f"Generate {needed} more unique titles for {category} {event_type} ({tone}). Avoid these existing titles: {', '.join(titles)}. Return JSON array only."
        
        result2 = smart_api_call(retry_system, retry_user, max_tokens + 20, temperature + 0.1, cost_mode=cost_mode)
        cleaned2 = clean_json_output(result2)
        
        try:
            parsed2 = json.loads(cleaned2)
            if isinstance(parsed2, list):
                for t in parsed2:
                    t = str(t).strip()
                    if t and 3 <= len(t.split()) <= 6 and t.lower() not in seen:
                        titles.append(t)
                        seen.add(t.lower())
                        if len(titles) >= num_titles:
                            break
        except Exception as e:
            lines = result2.replace('[', '').replace(']', '').replace('"', '').split(',')
            for line in lines:
                clean = line.strip().strip('"').strip("'").strip('-').strip('1234567890.').strip()
                if clean and 3 <= len(clean.split()) <= 6 and clean.lower() not in seen:
                    titles.append(clean)
                    seen.add(clean.lower())
                    if len(titles) >= num_titles:
                        break
    
    titles = titles[:num_titles]
    
    fallback_used = False
    creative_fallbacks = [
        f"{category} Excellence Summit",
        f"Future of {category}",
        f"{tone} {event_type} Experience",
        f"Next-Gen {category} Forum",
        f"Advanced {event_type} Series",
        f"{category} Innovation Hub",
        f"Premier {event_type} Event",
        f"{tone} {category} Gathering",
        f"Professional {event_type} Network",
        f"Elite {category} Conference"
    ]
    
    fallback_index = 0
    while len(titles) < num_titles and fallback_index < len(creative_fallbacks):
        candidate = creative_fallbacks[fallback_index]
        if candidate.lower() not in seen and 3 <= len(candidate.split()) <= 6:
            titles.append(candidate)
            seen.add(candidate.lower())
            fallback_used = True
        fallback_index += 1
    
    i = 1
    while len(titles) < num_titles:
        filler = f"{category} {event_type} {i}"
        if filler.lower() not in seen:
            titles.append(filler)
            seen.add(filler.lower())
            fallback_used = True
        i += 1
    
    end = time.time()
    
    prompt_tokens = count_tokens(system_msg) + count_tokens(user_msg)
    completion_tokens = count_tokens(result)
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(prompt_tokens, completion_tokens)
    efficiency_score = len(titles) / cost if cost > 0 else 0
    
    logs = {
        "Prompt tokens": prompt_tokens,
        "Completion tokens": completion_tokens,
        "Total tokens": total_tokens,
        "Time taken (s)": round(end - start, 2),
        "Estimated cost ($)": f"${cost:.5f}",
        "Efficiency score": round(efficiency_score, 2),
        "Model": "gpt-3.5-turbo",
        "System prompt": system_msg,
        "User prompt": user_msg,
        "Retry count": retry_count,
        "Titles requested": num_titles,
        "Titles generated": len(titles),
        "Cache hit": analytics.metrics['cache_hits'] > 0,
        "Overall efficiency": f"{analytics.get_efficiency_score():.1f}%",
        "Context used": bool(context and context.strip())
    }
    
    warnings = []
    if fallback_used:
        warnings.append(f"Some titles use creative fallbacks due to LLM output limits in {cost_mode} mode.")
    if parsing_error:
        warnings.append(f"JSON parsing issue: {parsing_error}")
    if retry_count > 0:
        warnings.append(f"Required {retry_count} retries to generate sufficient titles.")
    
    if warnings:
        logs["Warnings"] = "; ".join(warnings)
    
    return titles, logs

def generate_description(title, category, event_type, tone, context=None, max_chars=5000, cost_mode="balanced"):
    max_chars = max(100, min(int(max_chars), 5000))
    
    # Enhanced context handling for descriptions
    context_str = ""
    if context and context.strip():
        context_str = f"\n\nCRITICAL CONTEXT REQUIREMENTS:\n- Incorporate the following specific context: {context.strip()}\n- Ensure the description reflects the unique aspects mentioned in the context\n- Use context details to create more targeted and relevant content\n- Make the description more specific and aligned with the provided context\n- Avoid generic descriptions that don't reflect the context\n- Make the content highly relevant to the context provided"
    
    end_instruction = "Write in flowing paragraphs without bullet points or numbered lists. Use natural transitions between ideas. End with a strong call-to-action. No emojis or decorative symbols."
    if cost_mode == "economy":
        system_msg = f"Write compelling {tone.lower()} description for '{title}' - {category} {event_type}. EXACTLY {max_chars} characters. Include benefits and call-to-action. Use all available space. {end_instruction}{context_str}"
        user_msg = f"Description for: {title} ({category} {event_type}, {tone}) (MUST be {max_chars} characters){context_str}"
        max_tokens = int(max_chars/2.8) + 50
        temperature = 0.7
    elif cost_mode == "premium":
        system_msg = f"""Expert copywriter. Write compelling {max_chars}-character description for '{title}' - {tone.lower()} {event_type} in {category}.
Structure: Hook → Problem → Solution → Benefits → CTA
Tone: {tone.lower()}, persuasive, action-oriented
TARGET: Use the full {max_chars} characters available. Do not stop early. Fill all space. {end_instruction}{context_str}"""
        user_msg = f"Write description for '{title}' ({category} {event_type}, {tone}). MUST be as close as possible to {max_chars} characters.{context_str}"
        max_tokens = int(max_chars/2.5) + 100
        temperature = 0.75
    else:
        system_msg = f"""Professional copywriter. Create engaging {tone.lower()} description for '{title}' - {category} {event_type}.
Length: EXACTLY {max_chars} characters (use all available space, do not stop early)
Include: value proposition, benefits, call-to-action
Style: {tone.lower()}, compelling{context_str}
{end_instruction}"""
        user_msg = f"Write description: '{title}' ({category} {event_type}, {tone}). Target {max_chars} chars. Use all available space.{context_str}"
        max_tokens = int(max_chars/2.6) + 75
        temperature = 0.72
    
    start = time.time()
    
    try:
        description = smart_api_call(system_msg, user_msg, max_tokens, temperature, cost_mode=cost_mode)
        
        if len(description) < int(0.75 * max_chars) and cost_mode != "economy":
            remaining_chars = max_chars - len(description)
            extend_system = f"You are extending an event description. Add {remaining_chars} more characters to make it more detailed and compelling."
            extend_user = f"Current description: {description}\n\nExpand this by adding more details, benefits, or call-to-action to reach closer to {max_chars} total characters."
            
            extension = smart_api_call(extend_system, extend_user, int(remaining_chars/2.5) + 30, temperature, cost_mode=cost_mode)
            if extension and not extension.lower().startswith(description.lower()[:20]):
                description = description + " " + extension
        
    except Exception as e:
        return "", {"error": str(e)}
    
    end = time.time()
    
    prompt_tokens = count_tokens(system_msg) + count_tokens(user_msg)
    completion_tokens = count_tokens(description)
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(prompt_tokens, completion_tokens)
    too_short = len(description) < int(0.6 * max_chars)
    
    char_efficiency = len(description) / cost if cost > 0 else 0
    
    if len(description) > max_chars:
        description = description[:max_chars]
        if '.' in description:
            description = description[:description.rfind('.')+1]
    
    logs = {
        "Prompt tokens": prompt_tokens,
        "Completion tokens": completion_tokens,
        "Total tokens": total_tokens,
        "Time taken (s)": round(end - start, 2),
        "Estimated cost ($)": f"${cost:.5f}",
        "Cost per char": f"${cost/len(description):.8f}" if description else "$0",
        "Char efficiency": round(char_efficiency, 2),
        "Target utilization": f"{len(description)/max_chars*100:.1f}%",
        "Cost mode": cost_mode,
        "Shorter than requested": too_short,
        "category": category,
        "event_type": event_type,
        "tone": tone,
        "context": context,
        "max_chars": max_chars,
        "model": "gpt-3.5-turbo",
        "system_prompt": system_msg,
        "user_prompt": user_msg,
        "Context used": bool(context and context.strip())
    }
    
    return description, logs

def get_global_analytics():
    return {
        "total_requests": analytics.metrics['total_requests'],
        "cache_hits": analytics.metrics['cache_hits'],
        "cache_hit_rate": f"{(analytics.metrics['cache_hits'] / max(analytics.metrics['total_requests'], 1)) * 100:.1f}%",
        "total_cost": f"${analytics.metrics['total_cost']:.4f}",
        "total_tokens": analytics.metrics['total_tokens'],
        "avg_response_time": f"{analytics.metrics['avg_response_time']:.2f}s",
        "error_rate": f"{analytics.metrics['error_rate'] * 100:.1f}%",
        "efficiency_score": f"{analytics.get_efficiency_score():.1f}%",
        "cost_savings": f"${(analytics.metrics['cache_hits'] * 0.002):.4f}",
        "recommendations": get_optimization_recommendations()
    }

def get_optimization_recommendations():
    recommendations = []
    cache_rate = analytics.metrics['cache_hits'] / max(analytics.metrics['total_requests'], 1)
    avg_cost = analytics.metrics['total_cost'] / max(analytics.metrics['total_requests'], 1)
    
    if cache_rate < 0.2:
        recommendations.append("Use similar content parameters to boost cache efficiency (target: 60%+)")
    elif cache_rate < 0.5:
        recommendations.append("Good cache performance - try reusing successful prompts")
    
    if avg_cost > 0.008:
        recommendations.append("High cost per request - switch to economy mode to reduce by 40%")
    elif avg_cost > 0.005:
        recommendations.append("Moderate costs - consider economy mode for non-critical requests")
    
    if analytics.metrics['avg_response_time'] > 8:
        recommendations.append("Slow responses detected - cache will improve this significantly")
    elif analytics.metrics['avg_response_time'] > 5:
        recommendations.append("Response time acceptable - will improve with cache hits")
    
    if analytics.metrics['total_tokens'] / max(analytics.metrics['total_requests'], 1) > 1500:
        recommendations.append("High token usage - use economy mode for 25% token reduction")
    
    if analytics.metrics['error_rate'] > 0.05:
        recommendations.append("Error rate detected - verify API key and network stability")
    
    efficiency_score = analytics.get_efficiency_score()
    if efficiency_score > 80:
        recommendations.append("Excellent performance - system optimized")
    elif efficiency_score > 60:
        recommendations.append("Good performance - minor optimizations available")
    elif efficiency_score > 40:
        recommendations.append("Moderate efficiency - implement caching strategies")
    else:
        recommendations.append("Low efficiency - review cost mode and enable caching")
    
    return recommendations

def reset_analytics():
    global analytics
    analytics = PerformanceAnalytics()
    return "Analytics reset successfully" 