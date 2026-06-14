# Walkthrough - OpenRouter Settings Configuration and Verification

We have successfully performed the settings configuration flow and verified that both deployed web services—**AquaRAG Multi-Knowledge App** and **AquaRAG Exam App**—are fully operational using the **OpenRouter API** with the `liquid/lfm-2.5-1.2b-instruct:free` model.

The actions executed on the websites are detailed below.

---

## 1. AquaRAG Multi-Knowledge App Configuration & Verification
- **URL**: `https://aquarag-multi.onrender.com/`
- **Actions performed**:
  1. Opened the system settings modal using the ⚙️ button in the top right.
  2. Selected **OpenRouter API (免費/多模型)** as the provider.
  3. Pasted the OpenRouter API key (`sk-or-v1-5be96a...`).
  4. Configured the Model ID to `liquid/lfm-2.5-1.2b-instruct:free`.
  5. Saved the settings and verified that the configurations persisted in `localStorage`.
  6. Sent a query using a suggestion chip and confirmed that Traditional Chinese responses streamed successfully.

Here is the automated verification recording for the multi-knowledge app:
![AquaRAG Multi-Knowledge Settings Flow](/Users/albert/.gemini/antigravity-ide/brain/b433dbe8-039b-4662-9829-586b82e44ea7/openrouter_settings_multi_1781408654226.webp)

---

## 2. AquaRAG Exam App Configuration & Verification
- **URL**: `https://aquarag-exam.onrender.com/`
- **Actions performed**:
  1. Opened the system settings modal using the ⚙️ button.
  2. Selected **OpenRouter API (免費/多模型)** as the provider.
  3. Entered the OpenRouter API Key.
  4. Specified `liquid/lfm-2.5-1.2b-instruct:free` as the custom model.
  5. Clicked **儲存設定** to commit the settings.
  6. Clicked a suggestion chip ("淡水與海水硬骨魚滲透壓調節機制的差異？") to run a live chat query.
  7. Verified that the response was successfully retrieved, streamed, and translated into Traditional Chinese.

Here is the automated verification recording for the exam app:
![AquaRAG Exam Settings Flow](/Users/albert/.gemini/antigravity-ide/brain/b433dbe8-039b-4662-9829-586b82e44ea7/openrouter_settings_exam_1781409002990.webp)

### Final Chat Output
Below is the screenshot of the successful streaming response and document citations on the exam app:
![Exam RAG Chat Final Output](/Users/albert/.gemini/antigravity-ide/brain/b433dbe8-039b-4662-9829-586b82e44ea7/final_result_1781409155722.png)
