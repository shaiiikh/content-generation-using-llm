import streamlit as st
import os

try:
    from event_llm_core import generate_titles, generate_description, fuzzy_correct, get_global_analytics, reset_analytics
except Exception as e:
    st.error("**Configuration Error**")
    st.error("OpenAI API key is missing or invalid.")
    st.markdown("""
    ### How to fix this:
    
    **For Streamlit Cloud:**
    1. Go to your app settings
    2. Click on "Secrets" 
    3. Add: `OPENAI_API_KEY = "your_api_key_here"`
    
    **For local development:**
    1. Create a `.env` file
    2. Add: `OPENAI_API_KEY=your_api_key_here`
    
    **Get your API key:**
    - Visit: https://platform.openai.com/api-keys
    - Create a new secret key
    - Copy and paste it in the configuration above
    """)
    st.stop()

st.set_page_config(page_title="EC - 172", layout="wide")

st.markdown("""
<style>
section.main > div:first-child {background: #f8fafc; border-radius: 12px; padding: 2rem 2rem 1rem 2rem; box-shadow: 0 2px 8px #0001;}
.stSelectbox [data-baseweb="select"] > div {border-radius: 8px;}
.stButton > button {border-radius: 8px; background: #2563eb; color: #fff; font-weight: 600;}
.stSlider > div {color: #2563eb;}
.stTextInput > div > input {border-radius: 8px;}
.stTextArea > div > textarea {border-radius: 8px;}
.description-box {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #28a745;
    color: #333;
    line-height: 1.6;
    margin: 1rem 0;
}
.optimization-tip {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
    border-left: 4px solid #4299e1;
}
.context-highlight {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
    border-left: 4px solid #ff4757;
}
</style>
""", unsafe_allow_html=True)

st.title("EC-172")
st.write("Generate event titles and descriptions with advanced context-aware prompt engineering.")

def get_optimization_tip(category, event_type, tone):
    tips = {
        ("Technology", "Conference", "Professional"): "Technology conferences perform best with titles that emphasize innovation, future trends, and networking opportunities.",
        ("Technology", "Workshop", "Creative"): "Creative technology workshops work best when titles suggest hands-on learning and innovation.",
        ("Business", "Workshop", "Formal"): "Formal business workshops should highlight specific skills, ROI, and executive-level insights.",
        ("Business", "Conference", "Professional"): "Professional business conferences perform best with titles emphasizing leadership and strategic outcomes.",
        ("Education", "Seminar", "Creative"): "Creative education seminars work best when titles suggest transformation and hands-on learning.",
        ("Education", "Conference", "Innovative"): "Innovative education conferences should emphasize future learning methods and technology integration.",
        ("Health", "Workshop", "Friendly"): "Friendly health workshops perform best with approachable titles that emphasize wellness and community.",
        ("Entertainment", "Festival", "Casual"): "Casual entertainment festivals work best with energetic titles that create excitement.",
        ("Sports", "Conference", "Professional"): "Professional sports conferences should emphasize performance, strategy, and industry insights.",
        ("Arts & Culture", "Exhibition", "Creative"): "Creative arts exhibitions work best with inspiring titles that evoke curiosity and artistic expression."
    }
    
    key = (category, event_type, tone)
    if key in tips:
        return tips[key]
    
    return f"{tone} {event_type}s in {category} perform best when titles clearly communicate the unique value and target outcome."

def suggest_optimal_settings(category, event_type):
    suggestions = {
        ("Technology", "Conference"): {"tone": "Professional", "titles": 5, "desc_length": 1200},
        ("Technology", "Workshop"): {"tone": "Creative", "titles": 4, "desc_length": 800},
        ("Technology", "Seminar"): {"tone": "Professional", "titles": 4, "desc_length": 1000},
        ("Technology", "Webinar"): {"tone": "Innovative", "titles": 4, "desc_length": 900},
        ("Technology", "Festival"): {"tone": "Creative", "titles": 5, "desc_length": 1100},
        ("Technology", "Exhibition"): {"tone": "Professional", "titles": 4, "desc_length": 1000},
        ("Business", "Conference"): {"tone": "Professional", "titles": 5, "desc_length": 1400},
        ("Business", "Workshop"): {"tone": "Formal", "titles": 4, "desc_length": 900},
        ("Business", "Seminar"): {"tone": "Formal", "titles": 3, "desc_length": 1000},
        ("Business", "Webinar"): {"tone": "Professional", "titles": 4, "desc_length": 1000},
        ("Business", "Festival"): {"tone": "Professional", "titles": 4, "desc_length": 1200},
        ("Business", "Exhibition"): {"tone": "Professional", "titles": 4, "desc_length": 1100},
        ("Education", "Conference"): {"tone": "Innovative", "titles": 5, "desc_length": 1400},
        ("Education", "Workshop"): {"tone": "Creative", "titles": 4, "desc_length": 900},
        ("Education", "Seminar"): {"tone": "Innovative", "titles": 4, "desc_length": 1100},
        ("Education", "Webinar"): {"tone": "Creative", "titles": 5, "desc_length": 1000},
        ("Education", "Festival"): {"tone": "Creative", "titles": 5, "desc_length": 1200},
        ("Education", "Exhibition"): {"tone": "Innovative", "titles": 4, "desc_length": 1000},
        ("Health", "Conference"): {"tone": "Professional", "titles": 4, "desc_length": 1300},
        ("Health", "Workshop"): {"tone": "Friendly", "titles": 4, "desc_length": 900},
        ("Health", "Seminar"): {"tone": "Professional", "titles": 3, "desc_length": 800},
        ("Health", "Webinar"): {"tone": "Friendly", "titles": 4, "desc_length": 900},
        ("Health", "Festival"): {"tone": "Friendly", "titles": 5, "desc_length": 1100},
        ("Health", "Exhibition"): {"tone": "Professional", "titles": 4, "desc_length": 1000},
        ("Entertainment", "Conference"): {"tone": "Creative", "titles": 4, "desc_length": 1100},
        ("Entertainment", "Workshop"): {"tone": "Casual", "titles": 4, "desc_length": 800},
        ("Entertainment", "Seminar"): {"tone": "Creative", "titles": 3, "desc_length": 900},
        ("Entertainment", "Webinar"): {"tone": "Casual", "titles": 4, "desc_length": 800},
        ("Entertainment", "Festival"): {"tone": "Casual", "titles": 5, "desc_length": 1000},
        ("Entertainment", "Exhibition"): {"tone": "Creative", "titles": 5, "desc_length": 1100},
        ("Sports", "Conference"): {"tone": "Professional", "titles": 4, "desc_length": 1200},
        ("Sports", "Workshop"): {"tone": "Professional", "titles": 4, "desc_length": 900},
        ("Sports", "Seminar"): {"tone": "Professional", "titles": 3, "desc_length": 800},
        ("Sports", "Webinar"): {"tone": "Professional", "titles": 4, "desc_length": 900},
        ("Sports", "Festival"): {"tone": "Casual", "titles": 5, "desc_length": 1100},
        ("Sports", "Exhibition"): {"tone": "Professional", "titles": 4, "desc_length": 1000},
        ("Arts & Culture", "Conference"): {"tone": "Creative", "titles": 4, "desc_length": 1200},
        ("Arts & Culture", "Workshop"): {"tone": "Creative", "titles": 4, "desc_length": 900},
        ("Arts & Culture", "Seminar"): {"tone": "Creative", "titles": 3, "desc_length": 900},
        ("Arts & Culture", "Webinar"): {"tone": "Creative", "titles": 4, "desc_length": 800},
        ("Arts & Culture", "Festival"): {"tone": "Creative", "titles": 5, "desc_length": 1200},
        ("Arts & Culture", "Exhibition"): {"tone": "Creative", "titles": 5, "desc_length": 1100}
    }
    
    key = (category, event_type)
    return suggestions.get(key, {"tone": "Professional", "titles": 3, "desc_length": 800})

def get_combined_context():
    if not st.session_state.master_context and not st.session_state.context_updates:
        return None
    
    combined = st.session_state.master_context
    if st.session_state.context_updates:
        combined += " " + " ".join(st.session_state.context_updates)
    
    return combined.strip() if combined.strip() else None

def add_context_update(new_info):
    if new_info and new_info.strip():
        st.session_state.context_updates.append(new_info.strip())

def display_current_context():
    context = get_combined_context()
    if context:
        st.markdown(f'<div class="context-highlight"><strong>Current Context:</strong> {context}</div>', unsafe_allow_html=True)
    else:
        st.info("**Current Context:** None - Add context to improve generation quality!")

def validate_form_inputs(category, event_type, tone, required_fields=None):
    errors = []
    
    if category == "Select event category":
        errors.append("Please select an event category")
    
    if event_type == "Select event type":
        errors.append("Please select an event type")
    
    if tone == "Select tone of event":
        errors.append("Please select a tone for your event")
    
    if required_fields:
        for field_name, field_value in required_fields.items():
            if not field_value or field_value.strip() == "":
                errors.append(f"Please provide {field_name}")
    
    return errors

def show_validation_errors(errors):
    if errors:
        for error in errors:
            st.warning(f"{error}")
        return True
    return False

def show_context_input(step_name, key_suffix=""):
    st.markdown(f"### Add Context for {step_name}")
    st.markdown("**Context is crucial for high-quality generation!** Add specific details about your event:")
    
    context_examples = {
        "Title Generation": "e.g., Focus on AI and machine learning trends, Target executives and CTOs, Emphasize networking opportunities, Include specific technologies like blockchain or cloud computing...",
        "Description Generation": "e.g., Make it more focused on sustainability, Add networking aspects, Change the target audience to executives, Include specific benefits and outcomes, Emphasize hands-on learning..."
    }
    
    new_context = st.text_area(
        f"Additional context for {step_name}:",
        placeholder=context_examples.get(step_name, "Add specific details about your event..."),
        key=f"new_context_{key_suffix}",
        help="This context will be combined with your previous context and used for all future content generation. Be specific about your event's unique aspects!"
    )
    
    if st.button(f"Add Context for {step_name}", key=f"add_context_{key_suffix}"):
        if new_context:
            add_context_update(new_context)
            st.success(f"Context added: {new_context}")
            st.rerun()
        else:
            st.warning("Please enter some context to add.")
    
    return new_context

def initialize_session_state():
    session_vars = {
        'generated_titles': [],
        'final_title': "",
        'description': "",
        'final_description': "",
        'title_logs': None,
        'desc_logs': None,
        'master_context': "",
        'context_updates': []
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

initialize_session_state()

CATEGORY_OPTIONS = ["Select event category", "Technology", "Business", "Education", "Health", "Entertainment", "Sports", "Arts & Culture", "Other"]
EVENT_TYPE_OPTIONS = ["Select event type", "Conference", "Workshop", "Seminar", "Webinar", "Festival", "Exhibition", "Meetup", "Other"]
TONE_OPTIONS = ["Select tone of event", "Professional", "Casual", "Formal", "Creative", "Premium", "Innovative", "Friendly", "Corporate", "Other"]

st.markdown("## Context-Focused Title Generation")

# Initial context input
st.markdown("### Start with Context")
st.markdown("**Context is the key to great results!** Provide specific details about your event to get better titles and descriptions.")

initial_context = st.text_area(
    "What's your event about? (Be specific!):",
    placeholder="e.g., AI and machine learning conference for tech executives, focusing on networking and future trends, with hands-on workshops and keynote speakers from top tech companies...",
    key="initial_context",
    help="The more specific context you provide, the better your results will be. Include target audience, key themes, special features, etc."
)

if st.button("Set Initial Context", key="set_initial_context"):
    if initial_context and initial_context.strip():
        st.session_state.master_context = initial_context.strip()
        st.success("Initial context set! This will be used for all generation steps.")
        st.rerun()
    else:
        st.warning("Please provide some context about your event.")

col1, col2, col3 = st.columns(3)

with col1:
    title_category = st.selectbox("Category for Titles", CATEGORY_OPTIONS, index=1, key="title_category")
    if title_category == "Other":
        custom_title_category = st.text_input("Custom category", key="custom_title_category")
        if custom_title_category:
            suggestion = fuzzy_correct(custom_title_category, CATEGORY_OPTIONS[1:-1])
            if suggestion != custom_title_category:
                st.info(f"Did you mean: {suggestion}?")

with col2:
    title_event_type = st.selectbox("Event Type for Titles", EVENT_TYPE_OPTIONS, index=1, key="title_event_type")
    if title_event_type == "Other":
        custom_title_event_type = st.text_input("Custom event type", key="custom_title_event_type")
        if custom_title_event_type:
            suggestion = fuzzy_correct(custom_title_event_type, EVENT_TYPE_OPTIONS[1:-1])
            if suggestion != custom_title_event_type:
                st.info(f"Did you mean: {suggestion}?")

with col3:
    title_tone = st.selectbox("Tone for Titles", TONE_OPTIONS, index=1, key="title_tone")
    if title_tone == "Other":
        custom_title_tone = st.text_input("Custom tone", key="custom_title_tone")
        if custom_title_tone:
            suggestion = fuzzy_correct(custom_title_tone, TONE_OPTIONS[1:-1])
            if suggestion != custom_title_tone:
                st.info(f"Did you mean: {suggestion}?")

if title_category != "Select event category" and title_event_type != "Select event type":
    optimal = suggest_optimal_settings(title_category, title_event_type)
    st.markdown(f'<div class="optimization-tip">Optimization Suggestion: For {title_category} {title_event_type}s, recommended settings are {optimal["tone"]} tone with {optimal["titles"]} titles.</div>', unsafe_allow_html=True)

if title_category != "Select event category" and title_event_type != "Select event type" and title_tone != "Select tone of event":
    tip = get_optimization_tip(title_category, title_event_type, title_tone)
    st.info(tip)

with st.form("title_form", clear_on_submit=False):
    cost_mode = st.selectbox("Cost Optimization", ["balanced", "economy", "premium"], key="cost_mode")
    num_titles = st.slider("Number of Titles (max 5)", min_value=1, max_value=5, value=3)
    title_context = st.text_input("Additional Context for Titles (optional)", placeholder="e.g., Focus on AI and machine learning trends, target executives")
    generate_titles_btn = st.form_submit_button("Generate Titles")

if generate_titles_btn:
    final_category = custom_title_category if title_category == "Other" and custom_title_category else title_category
    final_event_type = custom_title_event_type if title_event_type == "Other" and custom_title_event_type else title_event_type
    final_tone = custom_title_tone if title_tone == "Other" and custom_title_tone else title_tone
    
    validation_errors = validate_form_inputs(final_category, final_event_type, final_tone)
    
    if show_validation_errors(validation_errors):
        st.stop()
    
    # Combine context
    combined_context = get_combined_context()
    if title_context and title_context.strip():
        if combined_context:
            combined_context += " " + title_context.strip()
        else:
            combined_context = title_context.strip()
    
    with st.spinner("Generating context-aware titles with advanced prompt engineering..."):
        try:
            titles, logs = generate_titles(
                final_category,
                final_event_type,
                final_tone,
                num_titles,
                combined_context,
                cost_mode
            )
            st.session_state.generated_titles = titles
            st.session_state.title_logs = logs
        except Exception as e:
            st.error(f"Error generating titles: {str(e)}")
            st.error("Please try again or check your API key.")

if st.session_state.get("generated_titles"):
    st.markdown("### Generated Titles:")
    for i, title in enumerate(st.session_state.generated_titles, 1):
        st.markdown(f'<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #2563eb; color: #333; margin-bottom: 0.5rem;">{i}. {title}</div>', unsafe_allow_html=True)
    st.download_button("Download Titles", "\n".join(st.session_state.generated_titles), file_name="event_titles.txt", mime="text/plain", key="download_titles_btn")
    
    display_current_context()
    show_context_input("Title Generation", "titles")
    
    if st.session_state.title_logs:
        show_title_analytics = st.button("View Title Generation Analytics", key="title_analytics_btn")
        if show_title_analytics:
            st.markdown("### Title Generation Analytics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Prompt Tokens", st.session_state.title_logs.get('Prompt tokens', 'N/A'))
                st.metric("Total Tokens", st.session_state.title_logs.get('Total tokens', 'N/A'))
            with col2:
                st.metric("Completion Tokens", st.session_state.title_logs.get('Completion tokens', 'N/A'))
                st.metric("Generation Time", f"{st.session_state.title_logs.get('Time taken (s)', 'N/A')}s")
            st.metric("Cost", st.session_state.title_logs.get('Estimated cost ($)', 'N/A'))
            st.markdown(f"**Model Used:** {st.session_state.title_logs.get('Model', 'gpt-3.5-turbo')}")
            with st.expander("Show Prompt Preview"):
                st.markdown(f"""
**System Prompt:**
```
{st.session_state.title_logs.get('System prompt', '')}
```
**User Prompt:**
```
{st.session_state.title_logs.get('User prompt', '')}
```
""", unsafe_allow_html=True)
    
    st.markdown("### Select or Create Your Title:")
    title_options = ["Select a title option..."] + [f"Use: {title}" for title in st.session_state.generated_titles] + ["Write my own custom title"]
    
    title_choice = st.selectbox("Choose how you want to proceed:", title_options, key="title_choice")
    
    if title_choice.startswith("Use: "):
        selected_generated_title = title_choice[5:]
        st.info(f"Selected title: **{selected_generated_title}**")
        
        edit_option = st.radio("What would you like to do?", 
                              ["Use this title as-is", "Edit this title"], 
                              key="edit_option")
        
        if edit_option == "Use this title as-is":
            st.session_state.final_title = selected_generated_title
            st.success(f"Final title: **{selected_generated_title}**")
        else:
            edited_title = st.text_input("Edit the title:", 
                                       value=selected_generated_title, 
                                       key="edit_selected_title")
            if edited_title:
                st.session_state.final_title = edited_title
                st.success(f"Final edited title: **{edited_title}**")
    
    elif title_choice == "Write my own custom title":
        custom_title = st.text_input("Write your own title:", 
                                   placeholder="Enter your custom event title...", 
                                   key="custom_title_input")
        if custom_title:
            suggestion = fuzzy_correct(custom_title, st.session_state.generated_titles)
            if suggestion != custom_title and suggestion in st.session_state.generated_titles:
                st.info(f"Did you mean one of our generated titles: **{suggestion}**?")
                use_suggestion = st.checkbox(f"Use '{suggestion}' instead?", key="use_fuzzy_suggestion")
                if use_suggestion:
                    st.session_state.final_title = suggestion
                    st.success(f"Final title (suggested): **{suggestion}**")
                else:
                    st.session_state.final_title = custom_title
                    st.success(f"Final custom title: **{custom_title}**")
            else:
                st.session_state.final_title = custom_title
                st.success(f"Final custom title: **{custom_title}**")

if st.session_state.get("final_title"):
    st.markdown("## Context-Aware Description Generation")
    
    desc_use_same = st.radio(
        "Description Content:",
        ["Use same title and settings as above", "Enter custom description parameters"],
        key="desc_use_same",
        help="Choose whether to use the selected title and previous settings or enter custom parameters."
    )
    
    with st.form("description_form", clear_on_submit=False):
        if desc_use_same == "Use same title and settings as above":
            desc_title = st.text_input("Title for Description", value=st.session_state.final_title, key="desc_title_input", disabled=True)
            desc_category = st.selectbox("Category for Description", ["Technology", "Business", "Education", "Health", "Entertainment", "Sports", "Arts & Culture", "Other"], 
                                       index=max(0, ["Technology", "Business", "Education", "Health", "Entertainment", "Sports", "Arts & Culture", "Other"].index(title_category) if title_category != "Select event category" else 0), 
                                       key="desc_category", disabled=True)
            desc_event_type = st.selectbox("Event Type for Description", ["Conference", "Workshop", "Seminar", "Webinar", "Festival", "Exhibition", "Meetup", "Other"],
                                         index=max(0, ["Conference", "Workshop", "Seminar", "Webinar", "Festival", "Exhibition", "Meetup", "Other"].index(title_event_type) if title_event_type != "Select event type" else 0),
                                         key="desc_event_type", disabled=True)
            desc_tone = st.selectbox("Tone for Description", ["Professional", "Casual", "Formal", "Creative", "Premium", "Innovative", "Friendly", "Corporate", "Other"],
                                   index=max(0, ["Professional", "Casual", "Formal", "Creative", "Premium", "Innovative", "Friendly", "Corporate", "Other"].index(title_tone) if title_tone != "Select tone of event" else 0),
                                   key="desc_tone", disabled=True)
            desc_context = st.text_input("Context for Description (optional)", value=get_combined_context() or "", key="desc_context", disabled=True)
            desc_cost_mode = st.selectbox("Description Cost Mode", ["balanced", "economy", "premium"], index=["balanced", "economy", "premium"].index(cost_mode), key="desc_cost_mode", disabled=True)
        else:
            desc_title = st.text_input("Title for Description", value=st.session_state.final_title, key="desc_title_input_custom")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                desc_category = st.selectbox("Category for Description", CATEGORY_OPTIONS, index=1, key="desc_category_custom")
                if desc_category == "Other":
                    custom_desc_category = st.text_input("Custom category", key="custom_desc_category")
                    if custom_desc_category:
                        suggestion = fuzzy_correct(custom_desc_category, CATEGORY_OPTIONS[1:-1])
                        if suggestion != custom_desc_category:
                            st.info(f"Did you mean: {suggestion}?")
            
            with col2:
                desc_event_type = st.selectbox("Event Type for Description", EVENT_TYPE_OPTIONS, index=1, key="desc_event_type_custom")
                if desc_event_type == "Other":
                    custom_desc_event_type = st.text_input("Custom event type", key="custom_desc_event_type")
                    if custom_desc_event_type:
                        suggestion = fuzzy_correct(custom_desc_event_type, EVENT_TYPE_OPTIONS[1:-1])
                        if suggestion != custom_desc_event_type:
                            st.info(f"Did you mean: {suggestion}?")
            
            with col3:
                desc_tone = st.selectbox("Tone for Description", TONE_OPTIONS, index=1, key="desc_tone_custom")
                if desc_tone == "Other":
                    custom_desc_tone = st.text_input("Custom tone", key="custom_desc_tone")
                    if custom_desc_tone:
                        suggestion = fuzzy_correct(custom_desc_tone, TONE_OPTIONS[1:-1])
                        if suggestion != custom_desc_tone:
                            st.info(f"Did you mean: {suggestion}?")
            
            desc_context = st.text_input("Context for Description (optional)", value="", key="desc_context_custom")
            desc_cost_mode = st.selectbox("Description Cost Mode", ["balanced", "economy", "premium"], key="desc_cost_mode_custom")
        
        max_chars = st.slider("Description Length (characters)", min_value=100, max_value=5000, value=800)
        generate_desc_btn = st.form_submit_button("Generate Description")

    if generate_desc_btn:
        if desc_use_same != "Use same title and settings as above":
            final_desc_category = custom_desc_category if desc_category == "Other" and custom_desc_category else desc_category
            final_desc_event_type = custom_desc_event_type if desc_event_type == "Other" and custom_desc_event_type else desc_event_type
            final_desc_tone = custom_desc_tone if desc_tone == "Other" and custom_desc_tone else desc_tone
        else:
            final_desc_category = desc_category
            final_desc_event_type = desc_event_type
            final_desc_tone = desc_tone
        
        # Combine context for description
        combined_context = get_combined_context()
        if desc_context and desc_context.strip():
            if combined_context:
                combined_context += " " + desc_context.strip()
            else:
                combined_context = desc_context.strip()
        
        with st.spinner("Generating context-aware description with advanced prompt engineering..."):
            try:
                description, logs = generate_description(
                    desc_title,
                    final_desc_category,
                    final_desc_event_type,
                    final_desc_tone,
                    combined_context,
                    max_chars,
                    desc_cost_mode
                )
                st.session_state.description = description
                st.session_state.desc_logs = logs
            except Exception as e:
                st.error(f"Error generating description: {str(e)}")
                st.error("Please try again or check your API key.")

    if st.session_state.get("description"):
        st.markdown("### Generated Description:")
        st.markdown(f'<div class="description-box">{st.session_state.description}</div>', unsafe_allow_html=True)
        st.info(f"Description length: {len(st.session_state.description)} characters")
        st.download_button("Download as .txt", st.session_state.description, file_name="event_description.txt", mime="text/plain", key="download_desc_btn")
        
        display_current_context()
        show_context_input("Description Generation", "description")
        
        if st.session_state.desc_logs:
            show_desc_analytics = st.button("View Description Generation Analytics", key="desc_analytics_btn")
            if show_desc_analytics:
                st.markdown("### Description Generation Analytics")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Prompt Tokens", st.session_state.desc_logs.get('Prompt tokens', 'N/A'))
                    st.metric("Total Tokens", st.session_state.desc_logs.get('Total tokens', 'N/A'))
                with col2:
                    st.metric("Completion Tokens", st.session_state.desc_logs.get('Completion tokens', 'N/A'))
                    st.metric("Generation Time", f"{st.session_state.desc_logs.get('Time taken (s)', 'N/A')}s")
                st.metric("Cost", st.session_state.desc_logs.get('Estimated cost ($)', 'N/A'))
                st.markdown(f"**Model Used:** {st.session_state.desc_logs.get('model', 'gpt-3.5-turbo')}")
                
        st.markdown("### Use This Description:")
        desc_options = ["Use generated description", "Edit generated description", "Write my own description"]
        desc_choice = st.selectbox("Choose how you want to proceed:", desc_options, key="desc_choice")
        
        if desc_choice == "Use generated description":
            st.session_state.final_description = st.session_state.description
            st.success(f"Using generated description ({len(st.session_state.description)} characters)")
        elif desc_choice == "Edit generated description":
            edited_desc = st.text_area("Edit the description:", 
                                     value=st.session_state.description, 
                                     key="edit_desc", height=150)
            if edited_desc:
                st.session_state.final_description = edited_desc
                st.success(f"Using edited description ({len(edited_desc)} characters)")
        else:
            custom_desc = st.text_area("Write your own description:", 
                                     placeholder="Enter your custom event description...", 
                                     key="custom_desc", height=150)
            if custom_desc:
                st.session_state.final_description = custom_desc
                st.success(f"Using custom description ({len(custom_desc)} characters)")

content_complete = (
    st.session_state.get("final_title") and 
    st.session_state.get("final_description")
)

if content_complete:
    st.markdown("---")
    st.markdown("## Complete Event Package")
    
    st.markdown("---")
    
    st.markdown("# EVENT SUMMARY")
    st.markdown("---")
    
    st.markdown("## TITLE")
    st.markdown(f"**{st.session_state.final_title}**")
    st.markdown("---")
    
    st.markdown("## DESCRIPTION")
    st.markdown(st.session_state.final_description)
    
    st.markdown("---")
    
    summary_text = f"""EVENT SUMMARY

TITLE:
{st.session_state.final_title}

DESCRIPTION:
{st.session_state.final_description}
"""
    
    st.download_button(
        "Download Complete Event Summary", 
        summary_text, 
        file_name="complete_event_summary.txt", 
        mime="text/plain", 
        key="download_complete_summary_btn"
    )

st.markdown("---")

with st.expander("System Performance Analytics", expanded=False):
    st.markdown("### Global Performance Metrics")
    
    try:
        analytics_data = get_global_analytics()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Requests", analytics_data["total_requests"])
            st.metric("Cache Hit Rate", analytics_data["cache_hit_rate"])
        with col2:
            st.metric("Total Cost", analytics_data["total_cost"])
            st.metric("Cost Savings", analytics_data["cost_savings"])
        with col3:
            st.metric("Avg Response Time", analytics_data["avg_response_time"])
            st.metric("Error Rate", analytics_data["error_rate"])
        with col4:
            st.metric("Efficiency Score", analytics_data["efficiency_score"])
            st.metric("Total Tokens", analytics_data["total_tokens"])
        
        st.markdown("### Optimization Recommendations")
        for rec in analytics_data["recommendations"]:
            st.info(f"• {rec}")
        
        if st.button("Reset Analytics", key="reset_analytics"):
            reset_analytics()
            st.success("Analytics reset successfully!")
            st.rerun()
            
    except Exception as e:
        st.error(f"Analytics unavailable: {str(e)}")

st.markdown("---")
st.markdown("**Context-Focused:** Advanced context-aware generation with intelligent prompt engineering for superior results.")