import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from image_generator import ImageGenerator
from gpt_service import GPTService

load_dotenv()

app = FastAPI()

os.makedirs("images", exist_ok=True)

images = {}

# Function to be run as a background task.
# This is just a placeholder function for demonstration.
# In your application, this could be a function that generates an image.
def write_log(message: str):
    # Example of a time-consuming task: Writing a message to a file.
    # Replace this with the logic of your image generation task.
    with open("log.txt", "a") as file:
        file.write(f"{message}\n")

@app.get("/example")
async def example_endpoint(background_tasks: BackgroundTasks):
    # This endpoint demonstrates how to add a background task.
    # The `write_log` function will be executed after the response is sent.
    # Note: The task runs in the same process but does not block the response.
    background_tasks.add_task(write_log, "Example endpoint was visited")
    return {"message": "This is an example endpoint"}

# TODO: Define your POST /images endpoint for asynchronous image generation
# This endpoint should accept a custom prompt, process it asynchronously,
# and return an image ID for later retrieval.

class ImagePrompt(BaseModel):
    character: str
    action: str     
    place: str = "in a workshop" 
    
@app.post("/images", status_code=202)
def create_image(prompt: ImagePrompt, background_tasks: BackgroundTasks):
    text = f"{prompt.character} {prompt.action} {prompt.place}"

    if contains_bad_words(text):
        raise HTTPException(status_code=400, detail="Your prompt contains inappropriate words.")

    image_id = str(uuid.uuid4())
    images[image_id] = "processing"
    background_tasks.add_task(gen_image_task, image_id, text)
    return {"image_id": image_id, "prompt": text}

# TODO: Implement the background task function for image generation
# This function will use the ImageGenerator service to generate images
# based on the provided custom prompt and save them.
def gen_image_task(image_id: str, text: str):
    try:
        generator = ImageGenerator(os.getenv("STABILITY_KEY"))
        image_bytes = generator.generate_image(text)

        # Stability returns nothing if its safety filter blocked the image
        if image_bytes is None:
            images[image_id] = "failed"
            return

        with open(f"images/{image_id}.png", "wb") as f:
            f.write(image_bytes)
        images[image_id] = "ready"
    except Exception as e:
        print("Image generation failed:", e)
        images[image_id] = "failed"

# TODO: Create an endpoint for retrieving generated images
# The endpoint should take an image ID and return the corresponding image
# if it's ready, or an appropriate status message otherwise.

@app.get("/image/{image_id}")
def get_image(image_id: str):
    check_image(image_id)
    return FileResponse(f"images/{image_id}.png", media_type="image/png")
    
# TODO: Implement error handling for various possible failure scenarios

def check_image(image_id: str):
    if image_id not in images:
        raise HTTPException(status_code=404, detail="Image not found")
    if images[image_id] == "processing":
        raise HTTPException(status_code=202, detail="Image is still processing, try again in a few seconds")
    if images[image_id] == "failed":
        raise HTTPException(status_code=500, detail="Image generation failed")
        
# OPTIONAL: Implement any necessary profanity checking or validation for the user prompts

def contains_bad_words(text: str) -> bool:
    if not os.getenv("OPENAI_API_KEY"):
        return False  # no key -> skip the check
    try:
        with open(os.getenv("PROFANITY_PROMPT_FILE", "profanity_prompt.txt")) as f:
            gpt = GPTService(os.getenv("OPENAI_API_KEY"), f.read())
        return gpt.contains_profanity(text)
    except Exception as e:
        print("Profanity check failed:", e)
        return False
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
