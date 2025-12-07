import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LogisticRegression

# Set page configuration
st.set_page_config(
    page_title="LinkedIn User Predictor",
    page_icon="💼",
    layout="wide"
)

# Load the trained model
@st.cache_resource
def load_model():
    # Always train the model at startup (cached per Streamlit session).
    s = pd.read_csv('social_media_usage.csv')

    def clean_sm(x):
        return np.where(x == 1, 1, 0)

    ss = pd.DataFrame({
        'sm_li': clean_sm(s['web1h']),
        'income': np.where(s['income'] > 9, np.nan, s['income']),
        'education': np.where(s['educ2'] > 8, np.nan, s['educ2']),
        'parent': np.where(s['par'] == 1, 1, np.where(s['par'] == 2, 0, np.nan)),
        'married': np.where(s['marital'] == 1, 1, np.where(s['marital'] == 2, 0, np.nan)),
        'female': np.where(s['gender'] == 2, 1, np.where(s['gender'] == 1, 0, np.nan)),
        'age': np.where(s['age'] > 98, np.nan, s['age'])
    }).dropna()

    X = ss[['income', 'education', 'parent', 'married', 'female', 'age']]
    y = ss['sm_li']

    with st.spinner('Training model — this may take a few seconds...'):
        model = LogisticRegression(class_weight='balanced', random_state=42, max_iter=1000)
        model.fit(X, y)

    return model

model = load_model()

# App title and description
st.title("💼 LinkedIn User Prediction App")
st.markdown("""
This application predicts whether an individual is likely to use LinkedIn based on demographic 
and socioeconomic factors. Use the sidebar to input characteristics and see the prediction results.
""")

st.markdown("---")

# Sidebar for user inputs
st.sidebar.header("📊 Input Demographics")
st.sidebar.markdown("Adjust the sliders and options below to input individual characteristics:")

# Income input
income = st.sidebar.slider(
    "Income Level",
    min_value=1,
    max_value=9,
    value=5,
    help="1=Less than $10k, 9=$150k+"
)

income_labels = {
    1: "Less than $10,000",
    2: "$10,000 to $20,000",
    3: "$20,000 to $30,000",
    4: "$30,000 to $40,000",
    5: "$40,000 to $50,000",
    6: "$50,000 to $75,000",
    7: "$75,000 to $100,000",
    8: "$100,000 to $150,000",
    9: "$150,000 or more"
}
st.sidebar.caption(f"Selected: {income_labels[income]}")

# Education input
education = st.sidebar.slider(
    "Education Level",
    min_value=1,
    max_value=8,
    value=4,
    help="1=Less than HS, 8=Postgraduate degree"
)

education_labels = {
    1: "Less than high school",
    2: "High school incomplete",
    3: "High school graduate",
    4: "Some college, no degree",
    5: "Associate degree",
    6: "Bachelor's degree",
    7: "Some graduate school",
    8: "Graduate degree"
}
st.sidebar.caption(f"Selected: {education_labels[education]}")

# Age input
age = st.sidebar.slider(
    "Age",
    min_value=18,
    max_value=97,
    value=42,
    help="Age in years"
)

# Binary inputs
st.sidebar.markdown("### Personal Status")
parent = st.sidebar.radio("Parent of child under 18?", ["No", "Yes"], horizontal=True)
parent_val = 1 if parent == "Yes" else 0

married = st.sidebar.radio("Married?", ["No", "Yes"], horizontal=True)
married_val = 1 if married == "Yes" else 0

female = st.sidebar.radio("Gender", ["Male", "Female"], horizontal=True)
female_val = 1 if female == "Female" else 0

# Create prediction button
predict_button = st.sidebar.button("🔮 Predict LinkedIn Usage", type="primary", use_container_width=True)

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Input Summary")
    
    # Display input summary
    summary_data = {
        "Characteristic": ["Income", "Education", "Age", "Parent", "Married", "Gender"],
        "Value": [
            income_labels[income],
            education_labels[education],
            f"{age} years",
            parent,
            married,
            female
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

with col2:
    st.subheader("🎯 Prediction Results")
    
    if predict_button:
        # Create input dataframe
        input_data = pd.DataFrame({
            'income': [income],
            'education': [education],
            'parent': [parent_val],
            'married': [married_val],
            'female': [female_val],
            'age': [age]
        })
        
        # Make prediction
        prediction = model.predict(input_data)[0]
        probability = model.predict_proba(input_data)[0]
        
        # Display results
        if prediction == 1:
            st.success("✅ **Predicted: LinkedIn User**")
        else:
            st.error("❌ **Predicted: Not a LinkedIn User**")
        
        # Display probabilities
        prob_linkedin = probability[1] * 100
        prob_not_linkedin = probability[0] * 100
        
        st.metric("Probability of Using LinkedIn", f"{prob_linkedin:.2f}%")
        st.metric("Probability of NOT Using LinkedIn", f"{prob_not_linkedin:.2f}%")
        
        # Confidence interpretation
        if prob_linkedin > 70:
            confidence = "High"
            color = "green"
        elif prob_linkedin > 50:
            confidence = "Moderate"
            color = "orange"
        else:
            confidence = "Low"
            color = "red"
        
        st.markdown(f"**Confidence Level:** :{color}[{confidence}]")

# Visualization section
st.markdown("---")
st.subheader("📊 Probability Visualization")

if predict_button:
    # Create probability chart
    fig, ax = plt.subplots(figsize=(10, 4))
    
    categories = ['Not LinkedIn User', 'LinkedIn User']
    probabilities = [prob_not_linkedin, prob_linkedin]
    colors = ['#ff6b6b', '#4ecdc4']
    
    bars = ax.barh(categories, probabilities, color=colors, alpha=0.8)
    ax.set_xlabel('Probability (%)', fontsize=12, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_title('LinkedIn Usage Probability', fontsize=14, fontweight='bold', pad=20)
    
    # Add percentage labels on bars
    for i, (bar, prob) in enumerate(zip(bars, probabilities)):
        ax.text(prob + 2, i, f'{prob:.1f}%', va='center', fontweight='bold', fontsize=11)
    
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    
    # Feature importance visualization
    st.markdown("---")
    st.subheader("🔍 Feature Importance")
    
    coefficients = model.coef_[0]
    features = ['Income', 'Education', 'Parent', 'Married', 'Female', 'Age']
    
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    colors_feat = ['green' if c > 0 else 'red' for c in coefficients]
    bars = ax2.barh(features, coefficients, color=colors_feat, alpha=0.7)
    ax2.set_xlabel('Coefficient Value', fontsize=12, fontweight='bold')
    ax2.set_title('Impact of Each Feature on LinkedIn Usage', fontsize=14, fontweight='bold', pad=20)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    st.pyplot(fig2)
    
    st.caption("Positive values (green) increase likelihood of LinkedIn usage. Negative values (red) decrease it.")

# Marketing insights section
st.markdown("---")
st.subheader("💡 Marketing Insights")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("**🎯 Primary Target**")
    st.markdown("""
    - High income ($75k+)
    - College educated
    - Ages 30-55
    - Professional careers
    """)

with col4:
    st.markdown("**📈 Key Predictors**")
    st.markdown("""
    - Income level (strongest)
    - Education level
    - Age (negative effect)
    - Professional status
    """)

with col5:
    st.markdown("**💼 Platform Strategy**")
    st.markdown("""
    - B2B marketing
    - Professional services
    - Career development
    - Networking events
    """)

# Footer
st.markdown("---")
st.caption("LinkedIn User Prediction Model | Built with Streamlit")
