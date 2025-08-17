from horizon import HorizonLLMClient  # Replace with your actual filename if different

def main():
    client = HorizonLLMClient()
    
    # Simple test message
    response = client.get_chat_response(user_msg="What's the capital of France?")
    
    print("Model Response:", response["model_answer"])

if __name__ == "__main__":
    main()
