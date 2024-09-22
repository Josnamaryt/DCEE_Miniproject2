import os
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# Load the CLIP model and processor
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch16")

# Sample dataset of products (for testing)
products = [
    {"name": "Red Dress", "description": "A beautiful red dress for summer.", "image_path": "images/red_dress.jpg"},
    {"name": "Blue Sneakers", "description": "Comfortable blue sneakers for running.", "image_path": "images/blue_sneakers.jpg"},
    {"name": "Green Backpack", "description": "Spacious green backpack for school.", "image_path": "images/green_backpack.jpg"},
]

def load_images(products):
    """Load images from the given product dataset."""
    images = []
    for product in products:
        if os.path.exists(product["image_path"]):
            images.append(Image.open(product["image_path"]))
        else:
            print(f"Image not found: {product['image_path']}")
    return images

def get_product_suggestions(user_prompt):
    """Get product suggestions based on user input."""
    descriptions = [product["description"] for product in products]
    images = load_images(products)

    # Process the inputs
    inputs = processor(text=[user_prompt] + descriptions, images=images, return_tensors="pt", padding=True)

    # Forward pass through CLIP
    with torch.no_grad():
        outputs = model(**inputs)

    # Get similarity scores
    logits_per_image = outputs.logits_per_image  # Image-text similarity scores
    probs = logits_per_image.softmax(dim=1).cpu().numpy()

    return probs[0], images

def main():
    print("Welcome to the Product Suggestion CLI!")
    user_prompt = input("Enter a product description: ")

    if user_prompt:
        probs, images = get_product_suggestions(user_prompt)
        sorted_indices = probs.argsort()[::-1]

        print("\nSuggested Products:")
        for index in sorted_indices:
            print(f"Product Name: {products[index]['name']}")
            print(f"Description: {products[index]['description']}")
            print(f"Similarity Score: {probs[index]:.2f}\n")
            images[index].show()  # Show the product image

if __name__ == "__main__":
    main()
