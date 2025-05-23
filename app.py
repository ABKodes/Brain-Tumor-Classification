import streamlit as st
import plotly.graph_objects as go
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import plotly.graph_objects as go
import cv2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Flatten
from tensorflow.keras.optimizers import Adamax
from tensorflow.keras.metrics import Precision, Recall
import google.generativeai as genai
import os

from mistralai import Mistral
import PIL.Image
from fpdf import FPDF
import time
import datetime
import random

api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

output_dir = 'saliency_map'
os.makedirs(output_dir, exist_ok=True)

def create_pdf_report(prediction, confidence, result, saliency_map_path):
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "Brain Tumor Classification App", align="C", ln=True)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Made by Dawit Zewdu @ December 2024", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Brain Tumor Classification Report", ln=True, align="C")
    pdf.ln(10)

    # Add Prediction Summary
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(0, 10, f"Predicted Class: {result}", ln=True)
    pdf.cell(0, 10, f"Confidence: {confidence * 100:.2f}%", ln=True)
    pdf.ln(10)

    # Add Saliency Map
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Saliency Map:", ln=True)
    pdf.image(saliency_map_path, x=50, y=None, w=100)  # Adjust size and positioning
    pdf.ln(10)

    # Explanation Section
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Explanation:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=explanation)
    pdf.ln(10)

    # Add Previous History Cases (Simulated AI-generated examples)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Previous History Cases:", ln=True)
    pdf.set_font("Arial", size=12)
    ex1 = generate_mock_case(prediction, confidence)
    ex2 = generate_mock_case(prediction, confidence)
    ex3 = generate_mock_case(prediction, confidence)
    cases = [
        ex1
    ]
    for case in cases:
        pdf.multi_cell(0, 10, txt=case)
        pdf.ln(10)

    # General Recommendations Section
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "General Recommendations:", ln=True)
    pdf.set_font("Arial", size=12)
    recommendations = (
        "1. Consult a neurologist or medical professional for confirmation.\n"
        "2. Bring this report to your doctor's appointment for a more informed discussion.\n"
        "3. Follow your doctor's advice for further diagnostic tests or treatment options.\n"
        "4. Maintain a healthy lifestyle, including regular check-ups, to monitor your brain health."
    )
    pdf.multi_cell(0, 10, txt=recommendations)
    pdf.ln(10)

    # Disclaimer Section
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Cautionary Disclaimer:", ln=True)
    pdf.set_font("Arial", size=12)
    disclaimer = (
        "This report is generated for informational purposes only and must not replace a doctor's consultation. "
        "The predictions made by this app are based on a deep learning model and should not be considered a definitive diagnosis. "
        "We strongly recommend consulting a qualified medical professional for confirmation and further guidance."
        "The previous cases that are listed here are simulated using AI, please understand that those are not real cases."
    )
    pdf.multi_cell(0, 10, txt=disclaimer)
    pdf.ln(10)

    # Save PDF to a temporary file
    report_path = os.path.join(output_dir, 'report.pdf')
    pdf.output(report_path)
    return report_path



def generate_mock_case(model_prediction, confidence):
    prompt = f"""
    Generate a mock history case (cases that happened before) based on the AI prediction and patient information:
        model_prediction (str): The predicted class from the model -> {model_prediction}.
        confidence (float): The confidence level of the prediction -> {confidence * 100:.2f}

    Return a single-line realistic mock case description based on the inputed information.

    Here are some examples of mock cases:
      if {model_prediction} == 'glioma':
        "Example 1: Glioma detected with {confidence * 100:.2f}% confidence. Patient exhibited early-stage symptoms and responded well to treatment."
      elif {model_prediction} == 'meningioma':
        "Example 2: Meningioma detected with {confidence * 100:.2f}% confidence. MRI indicated abnormal growth in the frontal lobe."
      elif {model_prediction} == 'pituitary':
        "Example 4: Pituitary tumor detected with {confidence * 100:.2f}% confidence. Patient underwent surgery and showed improvement post-treatment."
      else:
        "Example 3: No tumor detected. MRI confirmed no significant abnormalities."

    """


    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    response = model.generate_content([prompt], stream=False)

    return response.text


def generate_explanation_gemini(img_path, model_prediction, confidence):

    prompt = f"""You are an expert neurologist. You are tasked with explaining a saliency map of a brain tumor MRI scan.
    The saliency map was generated by a deep learning model that was trained to classify brain tumors
    as either glioma, meningioma, pituitary, or no tumor.

    The saliency map highlights the regions of the image that the machine learning model is focusing on to make the prediction.

    The deep learning model predicted the image to be of class '{model_prediction}' with a confidence of {confidence * 100}%.

    In your response:
    – Explain what regions of the brain the model is focusing on, based on the saliency map. Refer to the regions highlighted
    in light cyan, those are the regions where the model is focusing on.
    – Explain possible reasons why the model made the prediction it did.
    – Don’t mention anything like "The saliency map highlights the regions the model is focusing on, which are in light cyan"
    in your explanation.
    – Keep your explanation to 4 sentences max.

    Let's think step by step about this. Verify step by step.
    """

    img = PIL.Image.open(img_path)

    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    response = model.generate_content([prompt, img])

    return response.text

def generate_explanation_pixtral(img_path, model_prediction, confidence):

  prompt = f"""You are an expert neurologist. You are tasked with explaining a saliency map of a brain tumor MRI scan.
    The saliency map was generated by a deep learning model that was trained to classify brain tumors
    as either glioma, meningioma, pituitary, or no tumor.

    The saliency map highlights the regions of the image that the machine learning model is focusing on to make the prediction.

    The deep learning model predicted the image to be of class '{model_prediction}' with a confidence of {confidence * 100}%.

    In your response:
    – Explain what regions of the brain the model is focusing on, based on the saliency map. Refer to the regions highlighted
    in light cyan, those are the regions where the model is focusing on.
    – Explain possible reasons why the model made the prediction it did.
    – Don’t mention anything like "The saliency map highlights the regions the model is focusing on, which are in light cyan"
    in your explanation.
    – Keep your explanation to 4 sentences max.

    Let's think step by step about this. Verify step by step.
    """

  api_key = st.secrets["PIXTRAL_API_KEY"]
  img = PIL.Image.open(img_path)

  model = "pixtral-12b-2409"

  client = Mistral(api_key=api_key)

  chat_response = client.chat.complete(
      model= model,
      messages = [
          {
              "role": "user",
              "content": prompt,
          },
      ]
  )

  response = chat_response.choices[0].message.content


  return response


# Chat
def generate_chat_response_gemini(user_question, user_type, model_prediction, confidence, img_path):
  prompt = f"""You are an expert neurologist specializing in brain tumors. You have been asked to interpret and explain the results of an MRI scan.
  The scan was classified by a deep learning model as one of four categories: glioma, meningioma, pituitary tumor, or no tumor.
  The model predicts this MRI scan to be of class '{model_prediction}' with a confidence level of {confidence * 100}%.

  The user is a {user_type} and has asked the following question: {user_question}.

  When responding, keep the following in mind:

  If the user is a patient, avoid medical jargon and provide an explanation that is clear and accessible to someone with no medical background. Keep it simple and reassuring.
  Do not adopt a formal doctor's role; just provide information based on the question without suggesting appointments, further steps, or treatment options.
  Use a step-by-step approach in your response to ensure clarity and thoroughness.
  Be brief in your responses.

  Let's think step by step about this. Verify step by step.

  """
  img = PIL.Image.open(img_path)

  model = genai.GenerativeModel(model_name="gemini-1.5-flash")
  response = model.generate_content([prompt, img], stream=True)

  for chunk in response:
    yield chunk.text




def generate_saliency_map(model, img_array, class_index, img_size):
    with tf.GradientTape() as tape:
        img_tensor = tf.convert_to_tensor(img_array)
        tape.watch(img_tensor)
        predictions = model(img_tensor)
        target_class = predictions[:, class_index]

    gradients = tape.gradient(target_class, img_tensor)
    gradients = tf.math.abs(gradients)
    gradients = tf.reduce_max(gradients, axis=-1)
    gradients = gradients.numpy().squeeze()

    gradients = cv2.resize(gradients, img_size)

    center = (gradients.shape[0] // 2, gradients.shape[1] // 2)
    radius = min(center[0], center[1]) - 10
    y, x = np.ogrid[:gradients.shape[0], :gradients.shape[1]]
    mask = (x - center[0])** 2 + (y - center[1])** 2 <= radius**2

    gradients = gradients * mask

    brain_gradients = gradients[mask]
    if brain_gradients.max() > brain_gradients.min():
        brain_gradients = (brain_gradients - brain_gradients.min()) / (brain_gradients.max() - brain_gradients.min())
    gradients[mask] = brain_gradients

    # Apply a higher threshold
    threshold = np.percentile(gradients[mask], 80)
    gradients[gradients < threshold] = 0

    # Apply more aggressive smoothing
    gradients = cv2.GaussianBlur(gradients, (11, 11), 0)

    # Create a heatmap overlay with enhanced contrast
    heatmap = cv2.applyColorMap(np.uint8(255 * gradients), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    # Resize heatmap to match original image size
    heatmap = cv2.resize(heatmap, img_size)

    # Superimpose the heatmap on original image with increased opacity
    original_img = image.img_to_array(img)
    superimposed_img = heatmap * 0.7 + original_img * 0.3
    superimposed_img = superimposed_img.astype(np.uint8)

    img_path = os.path.join(output_dir, uploaded_file.name)
    with open(img_path, 'wb') as f:
      f.write(uploaded_file.getbuffer())

    saliency_map_path = f'saliency_map/{uploaded_file.name}'

    # save the saliency map
    cv2.imwrite(saliency_map_path, cv2.cvtColor(superimposed_img, cv2.COLOR_RGB2BGR))

    return superimposed_img


def load_xception_model(path):
  img_shape = (299, 299, 3)
  base_model = tf.keras.applications.Xception(include_top=False, weights="imagenet", input_shape=img_shape, pooling='max')

  model = Sequential([
      base_model,
      Flatten(),
      Dropout(rate=0.3),
      Dense(128, activation='relu'),
      Dropout(rate=0.25),
      Dense(4, activation='softmax')
  ])

  model.build((None,) + img_shape)

  model.compile(Adamax(learning_rate=0.01),
                loss="categorical_crossentropy",
                metrics=['accuracy', Precision(), Recall()])
  model.load_weights(path)

  return model


st.set_page_config(
    page_title="Brain Tumor Classification",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded")

st.title('Brain Tumor Classification')

col = st.columns((1.5, 4.5, 2), gap='medium')


with col[1]:
  st.write("Upload an image of a brain MRI scan to classify.")
  uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])


  if uploaded_file is not None:
      selected_model = st.radio(
          "Select a model:",
          ("Transfer Learning - Xception", "Custom CNN")
      )

      if selected_model == "Transfer Learning - Xception":
        with st.spinner('Generating prediction...'):
          model = load_xception_model('trained_xception_model.weights.h5')
          img_size = (299, 299)
      else:
        with st.spinner('Generating prediction...'):
          model = load_model('trained_cnn_model.h5')
          img_size = (224, 224)


      labels = ['Glioma', 'Meningioma', 'No tumor', 'Pituitary']
      img = image.load_img(uploaded_file, target_size=img_size)
      img_array = image.img_to_array(img)
      img_array = np.expand_dims(img_array, axis=0)
      img_array /= 255.0

      prediction = model.predict(img_array)

      # Get the class with the highest probability
      class_index = np.argmax(prediction[0])
      result = labels[class_index]

with col[0]:
  if uploaded_file is not None:
    # Assuming prediction and labels are already defined
    probabilities = prediction[0]
    sorted_indices = np.argsort(probabilities)[::-1]
    sorted_labels = [labels[i] for i in sorted_indices]
    sorted_probabilities = probabilities[sorted_indices]

    # Set colors for the segments
    colors = ['blue' if label != result else 'red' for label in sorted_labels]

    # Initialize a list to store the donut chart data
    fig = go.Figure()

    # Define the gap factor to control spacing between donuts
    gap_factor = 2 # Increase this value for larger gaps
    dsf = 0.01  # Donut scaling factor

    # Create each donut segment and stack them vertically
    for i, (label, prob) in enumerate(zip(sorted_labels, sorted_probabilities)):
      start_y = 1 - ((i + 1) / len(sorted_labels)) + gap_factor / 2
      end_y = 1 - (i / len(sorted_labels)) - gap_factor / 2

      fig.add_trace(go.Pie(
            # labels=[label, '']p,
            values=[prob * 100, 100 - prob * 100],
            hole=0.6,
            # textinfo='',
            marker=dict(colors=[colors[i], 'black']),
            domain={'y': [1 - (i + 1) / len(sorted_labels), 1 - i / len(sorted_labels)], 'x': [0, 1]},
            showlegend=False
        ))

    # Customize layout
    fig.update_layout(
        title='Tumor Probabilities',
        height=1100,
        width=200,
        annotations=[
            # dict(text=f'{sorted_labels[i]}<br>{prob * 100:.2f}%', x=0.5, y=1 - (i + 0.5) / len(sorted_labels), showarrow=False)
            dict(text=f'{sorted_labels[i]}<br>{prob * 100:.2f}%', x=0.5, y=1 - (i + 0.5) / len(sorted_labels), showarrow=False)
            for i, prob in enumerate(sorted_probabilities)
        ]
    )

    # Render the Plotly chart in Streamlit
    st.plotly_chart(fig)


with col[1]:
  if uploaded_file is not None:
    # Generate the saliency map
    saliency_map = generate_saliency_map(model, img_array, class_index, img_size)

    # Display the two images side by side
    col1, col2 = st.columns(2)
    with col1:
      st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
    with col2:
      st.image(saliency_map, caption="Saliency Map", use_container_width=True)

    result_container = st.container()
    result_container = st.container()

    result_container.markdown(
    f"""
    <div style="background: linear-gradient(135deg, #1c1c1c, #333333); color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="flex: 1; text-align: center;">
            <h3 style="color: #e0e0e0; margin-bottom: 10px; font-size: 20px; text-transform: uppercase; letter-spacing: 1px;">Prediction</h3>
            <h3 style="font-size: 36px; font-weight: 800; color: #FF4C4C; margin: 0; text-shadow: 0 2px 5px rgba(255, 76, 76, 0.6);">
                {result}
            </h3>
        </div>
        <div style="width: 2px; height: 80px; background: linear-gradient(180deg, #ffffff, #888888); margin: 0 20px;"></div>
        <div style="flex: 1; text-align: center;">
            <h3 style="color: #e0e0e0; margin-bottom: 10px; font-size: 20px; text-transform: uppercase; letter-spacing: 1px;">Confidence</h3>
            <h3 style="font-size: 36px; font-weight: 800; color: #4CAFFF; margin: 0; text-shadow: 0 2px 5px rgba(76, 175, 255, 0.6);">
                {prediction[0][class_index] * 100 :.2f}%
            </h3>
        </div>
    </div>
    </div>

      """,
      unsafe_allow_html=True
    )



with col[2]:
  if uploaded_file is not None:

    # Explanation
    st.write("## Explanation")
    saliency_map_path = f'saliency_map/{uploaded_file.name}'

    llm_model_for_exp = st.radio("Select a model to explain the images to you:", ("Please select...", "gemini-1.5-flash", "pixtral-12b-2409"))
    if llm_model_for_exp == "gemini-1.5-flash":
      with st.spinner('Generating explantion...'):
        explanation = generate_explanation_gemini(saliency_map_path, result, prediction[0][class_index])
        st.write(explanation)
    elif llm_model_for_exp == "pixtral-12b-2409":
      with st.spinner('Generating explantion...'):
        explanation = generate_explanation_pixtral(saliency_map_path, result, prediction[0][class_index])
        st.write(explanation)
    else:
      st.warning("Please select your model to generate explanation.")
      explanation = ""

    if explanation != "":
        # Generate and allow download of the report
        if "downloaded" not in st.session_state:
            st.session_state.downloaded = False
            st.session_state.show_message = False

        st.write("## Download Report")
        with st.spinner('Generating report...'):

            # Create a downloadable pdf that is a report on the findings
            report_path = create_pdf_report(
                    prediction=prediction[0],
                    confidence=prediction[0][class_index],
                    result=result,
                    saliency_map_path=saliency_map_path
                )
        with open(report_path, "rb") as f:
              if st.download_button(
                label="Download Report as PDF",
                data=f,
                file_name="Brain_Tumor_Classification_Report.pdf",
                mime="application/pdf"
              ):


                st.session_state.downloaded = True
                st.session_state.show_message = True

        if st.session_state.downloaded:
          st.success("The report has been successfully downloaded!")
          time.sleep(5)  # Wait for 5 seconds
          st.session_state.show_message = False



with col[2]:
  if uploaded_file is not None:
    # Chat interface
    st.write("## MRI Chat")
    user_type = st.radio("I am the:", ("Please select...", "Patient", "Doctor"))

    # Display a warning message if the user hasn't selected a valid option
    if user_type == "Please select...":
        st.warning("Please select your user type before asking a question.")
    else:

      # Chat Interface
      st.title("MRI Bot")

      # Set up the chat container with a fixed height
      with st.container():
          st.markdown("""
              <style>
              .chat-container {
                  height: 400px;
                  display: flex;
                  flex-direction: column;
                  justify-content: flex-end;
                  overflow-y: auto;
                  border: 1px solid #ccc;
                  padding: 10px;
              }
              </style>
          """, unsafe_allow_html=True)

          # Wrap chat messages in a container for custom styling
          chat_container = st.empty()
          with chat_container.container():
              # initialize the chat history
              if "messages" not in st.session_state:
                  intro_message = "Is there anything more you would like me to explain about the MRI Scan?"
                  st.session_state.messages = [{"role": "assistant", "content": intro_message}]

              # Display chat messages from history on app rerun
              for message in st.session_state.messages:
                  with st.chat_message(message["role"]):
                      st.markdown(message["content"])

          # Pin chat_input to the bottom
          user_question = st.chat_input("Ask a follow question about the MRI scan")
          if user_question:
              # Display user message in chat message container
              st.session_state.messages.append({"role": "user", "content": user_question})
              # chat_container.empty()  # Clear container to refresh chat

              with chat_container.container(height=400):
                  for message in st.session_state.messages:
                      with st.chat_message(message["role"]):
                          st.markdown(message["content"])
                  # Add new messages dynamically
                  # st.chat_message("user").markdown(user_question)

                  # Display assistant response in chat message container
                  with st.chat_message("assistant"):
                      with st.spinner('Generating response...'):
                          full_response = ''
                          for response in generate_chat_response_gemini(user_question, user_type, result, prediction[0][class_index], saliency_map_path):
                              full_response += response
                              st.markdown(response)
                          # st.markdown(full_response)

                  # Add assistant response to chat history
                  st.session_state.messages.append({"role": "assistant", "content": full_response})
