import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Page config
st.set_page_config(page_title="LinkedIn User Predictor", page_icon="💼", layout="wide")

# Title
st.title("💼 LinkedIn User Prediction App")
st.markdown("Predict whether someone uses LinkedIn based on demographic information")

# Load and prepare data
@st.cache_data
def load_and_prepare_data():
    # Load data
    s = pd.read_csv('social_media_usage.csv')
    
    # Clean function
    def clean_sm(x):
        return np.where(x == 1, 1, 0)
    
    # Create clean dataframe
    ss = pd.DataFrame({
        'sm_li': clean_sm(s['web1h']),
        'income': np.where(s['income'] > 9, np.nan, s['income']),
        'education': np.where(s['educ2'] > 8, np.nan, s['educ2']),
        'parent': np.where(s['par'] == 1, 1, np.where(s['par'] == 2, 0, np.nan)),
        'married': np.where(s['marital'] == 1, 1, np.where(s['marital'] == 2, 0, np.nan)),
        'female': np.where(s['gender'] == 2, 1, np.where(s['gender'] == 1, 0, np.nan)),
        'age': np.where(s['age'] > 98, np.nan, s['age'])
    })
    
    # Drop missing values
    ss = ss.dropna()
    
    return ss

# Train model
@st.cache_resource
def train_model(ss):
    # Features and target
    X = ss[['income', 'education', 'parent', 'married', 'female', 'age']]
    y = ss['sm_li']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train model
    lr = LogisticRegression(class_weight='balanced', random_state=42)
    lr.fit(X_train, y_train)
    
    return lr

# Load data and train model
ss = load_and_prepare_data()
model = train_model(ss)

st.markdown("---")

# Sidebar inputs
st.sidebar.header("📊 Enter Person's Information")

income = st.sidebar.slider("Income Level (1=<$10k, 9=$150k+)", 1, 9, 5)
education = st.sidebar.slider("Education Level (1=<HS, 8=Grad)", 1, 8, 4)
age = st.sidebar.slider("Age", 18, 97, 42)

st.sidebar.markdown("### Personal Status")
parent = st.sidebar.radio("Parent?", ["No", "Yes"])
married = st.sidebar.radio("Married?", ["No", "Yes"])
female = st.sidebar.radio("Gender", ["Male", "Female"])

# Convert to numeric
parent_val = 1 if parent == "Yes" else 0
married_val = 1 if married == "Yes" else 0
female_val = 1 if female == "Female" else 0

# Main content
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Input Summary")
    
    income_labels = {
        1: "Less than $10,000", 2: "$10,000-$20,000", 3: "$20,000-$30,000",
        4: "$30,000-$40,000", 5: "$40,000-$50,000", 6: "$50,000-$75,000",
        7: "$75,000-$100,000", 8: "$100,000-$150,000", 9: "$150,000+"
    }
    
    education_labels = {
        1: "Less than HS", 2: "HS incomplete", 3: "HS graduate",
        4: "Some college", 5: "Associate", 6: "Bachelor's",
        7: "Some grad school", 8: "Graduate degree"
    }
    
    st.write(f"**Income:** {income_labels[income]}")
    st.write(f"**Education:** {education_labels[education]}")
    st.write(f"**Age:** {age}")
    st.write(f"**Parent:** {parent}")
    st.write(f"**Married:** {married}")
    st.write(f"**Gender:** {female}")

with col2:
    st.subheader("🎯 Prediction")
    
    # Make prediction
    person = pd.DataFrame({
        'income': [income],
        'education': [education],
        'parent': [parent_val],
        'married': [married_val],
        'female': [female_val],
        'age': [age]
    })
    
    prediction = model.predict(person)[0]
    probability = model.predict_proba(person)[0]
    
    # Display result
    if prediction == 1:
        st.success("✅ Predicted: LinkedIn User")
    else:
        st.error("❌ Predicted: Not a LinkedIn User")
    
    # Probabilities
    prob_linkedin = probability[1] * 100
    prob_not = probability[0] * 100
    
    st.metric("LinkedIn Usage Probability", f"{prob_linkedin:.1f}%")
    st.metric("Not Using LinkedIn Probability", f"{prob_not:.1f}%")

# Visualization
st.markdown("---")
st.subheader("📊 Probability Breakdown")

fig, ax = plt.subplots(figsize=(10, 4))
categories = ['Not LinkedIn User', 'LinkedIn User']
probs = [prob_not, prob_linkedin]
colors = ['#ff6b6b', '#4ecdc4']

bars = ax.barh(categories, probs, color=colors, alpha=0.8)
ax.set_xlabel('Probability (%)', fontsize=12)
ax.set_xlim(0, 100)
ax.set_title('Prediction Probabilities', fontsize=14, fontweight='bold')

for i, (bar, prob) in enumerate(zip(bars, probs)):
    ax.text(prob + 2, i, f'{prob:.1f}%', va='center', fontweight='bold')

ax.grid(axis='x', alpha=0.3)
st.pyplot(fig)

# Feature importance
st.markdown("---")
st.subheader("🔍 Feature Importance")

coef = model.coef_[0]
features = ['Income', 'Education', 'Parent', 'Married', 'Female', 'Age']

fig2, ax2 = plt.subplots(figsize=(10, 4))
colors_feat = ['green' if c > 0 else 'red' for c in coef]
ax2.barh(features, coef, color=colors_feat, alpha=0.7)
ax2.set_xlabel('Coefficient', fontsize=12)
ax2.set_title('How Each Factor Affects LinkedIn Usage', fontsize=14, fontweight='bold')
ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
ax2.grid(axis='x', alpha=0.3)
st.pyplot(fig2)

st.caption("Green = increases likelihood, Red = decreases likelihood")

# Marketing insights
st.markdown("---")
st.subheader("💡 Marketing Insights")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("**🎯 Best Target**")
    st.markdown("- High income\n- College educated\n- Ages 30-55")

with col4:
    st.markdown("**📈 Key Drivers**")
    st.markdown("- Income level\n- Education\n- Age (younger)")

with col5:
    st.markdown("**💼 Strategy**")
    st.markdown("- B2B marketing\n- Professional services\n- Career content")
