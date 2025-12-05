# Quick Start Guide - LinkedIn Prediction Project

## Files You Need

### For Part 1 (Jupyter Notebook):
- `linkedin_prediction.ipynb` - The main notebook (SIMPLE VERSION)
- `social_media_usage.csv` - The dataset

### For Part 2 (Streamlit App):
- `streamlit_app_simple.py` - The app (builds model from scratch)
- `social_media_usage.csv` - The dataset
- `requirements.txt` - Required packages

## How to Run

### Part 1: Run the Jupyter Notebook

1. Put `linkedin_prediction.ipynb` and `social_media_usage.csv` in the same folder
2. Open the notebook in Jupyter
3. Run all cells from top to bottom
4. The notebook will:
   - Clean the data
   - Create visualizations
   - Train the model
   - Calculate all metrics by hand
   - Make predictions

5. Export to HTML: File → Download as → HTML

### Part 2: Run the Streamlit App

1. Install packages:
```bash
pip install streamlit pandas numpy scikit-learn matplotlib
```

2. Make sure these files are in the same folder:
   - `streamlit_app_simple.py`
   - `social_media_usage.csv`

3. Run the app:
```bash
streamlit run streamlit_app_simple.py
```

4. The app will open in your browser

5. Record your demo:
   - Use Zoom screen recording (or any screen recorder)
   - Show adjusting the input sliders
   - Make predictions for different people
   - Show the visualizations
   - Keep it 1-2 minutes

## Key Differences from Before

**Now the project builds everything from scratch:**
- ✅ The notebook trains the model step-by-step
- ✅ The Streamlit app loads the data and trains its own model
- ✅ No pre-trained model file needed
- ✅ Everything is done by you!

## What the Streamlit App Does

1. Loads `social_media_usage.csv`
2. Cleans the data (same as notebook)
3. Trains a logistic regression model
4. Uses the trained model to make predictions based on user inputs
5. Shows probabilities and visualizations

## Tips for Demo Video

- Start by showing the app interface
- Adjust a few different combinations of inputs
- Point out how probabilities change
- Show the feature importance chart
- Mention marketing insights
- Keep it under 2 minutes!

## Questions?

The code is well-commented. Read through the notebook to understand each step.
Both files do the same thing - train a model from the data!
