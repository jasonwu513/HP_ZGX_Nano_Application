from fastapi import FastAPI, UploadFile, File
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import torch
import uvicorn
import librosa
import io

app = FastAPI(title="Qwen3-ASR-0.6B Microservice")

model = None
processor = None

@app.on_event("startup")
def load_model():
    global model, processor
    print("正在載入真正的 Qwen3-ASR-0.6B 模型...")
    
    # 官方正確的 Model ID
    model_id = "Qwen/Qwen3-ASR-0.6B" 
    
    # 根據是否有 GPU 決定精度，並讓 Transformers 自動分配記憶體
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, 
        torch_dtype=dtype, 
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)
    print("模型載入完成！")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 讀取音檔
    audio_bytes = await file.read()
    
    # Qwen3-ASR 需要 16000Hz 採樣率
    audio, rate = librosa.load(io.BytesIO(audio_bytes), sr=16000)
    
    # 透過 Processor 將音訊轉換為特徵張量
    inputs = processor(audio, return_tensors="pt", sampling_rate=16000)
    
    # 將張量搬移到模型所在的設備 (GPU/CPU) 並對齊精度
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    if "input_features" in inputs:
        inputs["input_features"] = inputs["input_features"].to(model.dtype)
    
    # 執行推論 (原生的 generate 方法效能最好)
    with torch.no_grad():
        outputs = model.generate(**inputs)
        
    # 將輸出的 Token 解碼回人類可讀的中文/英文文字
    transcript = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    
    return {"filename": file.filename, "transcript": transcript}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)from fastapi import FastAPI, UploadFile, File
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import torch
import uvicorn
import librosa
import io

app = FastAPI(title="Qwen3-ASR-0.6B Microservice")

model = None
processor = None

@app.on_event("startup")
def load_model():
    global model, processor
    print("正在載入真正的 Qwen3-ASR-0.6B 模型...")
    
    # 官方正確的 Model ID
    model_id = "Qwen/Qwen3-ASR-0.6B" 
    
    # 根據是否有 GPU 決定精度，並讓 Transformers 自動分配記憶體
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, 
        torch_dtype=dtype, 
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_id)
    print("模型載入完成！")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 讀取音檔
    audio_bytes = await file.read()
    
    # Qwen3-ASR 需要 16000Hz 採樣率
    audio, rate = librosa.load(io.BytesIO(audio_bytes), sr=16000)
    
    # 透過 Processor 將音訊轉換為特徵張量
    inputs = processor(audio, return_tensors="pt", sampling_rate=16000)
    
    # 將張量搬移到模型所在的設備 (GPU/CPU) 並對齊精度
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    if "input_features" in inputs:
        inputs["input_features"] = inputs["input_features"].to(model.dtype)
    
    # 執行推論 (原生的 generate 方法效能最好)
    with torch.no_grad():
        outputs = model.generate(**inputs)
        
    # 將輸出的 Token 解碼回人類可讀的中文/英文文字
    transcript = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    
    return {"filename": file.filename, "transcript": transcript}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
