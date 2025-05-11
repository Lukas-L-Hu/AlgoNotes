import boto3
import json
import os
from dotenv import load_dotenv

def test_model(model_id):
    """Test a specific Bedrock model with a simple prompt"""
    
    # Load environment variables
    load_dotenv()
    
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    print(f"Testing Bedrock model: {model_id}")
    print(f"Using region: {region}")
    
    # Create Bedrock runtime client
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token
    )
    
    # Determine model provider
    model_provider = model_id.split('.')[0].lower()
    print(f"Detected provider: {model_provider}")
    
    # Create appropriate request body based on the model provider
    if "anthropic" in model_provider:
        # Claude models
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, what can you help me with today?"
                }
            ],
            "temperature": 0.5
        })
        print("Using Anthropic Claude format")
        
    elif "amazon" in model_provider:
        # Amazon Titan models
        body = json.dumps({
            "inputText": "Hello, what can you help me with today?",
            "textGenerationConfig": {
                "maxTokenCount": 100,
                "temperature": 0.5,
                "topP": 0.9
            }
        })
        print("Using Amazon Titan format")
        
    elif "ai21" in model_provider:
        # AI21 Jurassic models
        body = json.dumps({
            "prompt": "Hello, what can you help me with today?",
            "maxTokens": 100,
            "temperature": 0.5,
            "topP": 0.9
        })
        print("Using AI21 format")
        
    elif "cohere" in model_provider:
        # Cohere models
        body = json.dumps({
            "prompt": "Hello, what can you help me with today?",
            "max_tokens": 100,
            "temperature": 0.5
        })
        print("Using Cohere format")
        
    elif "meta" in model_provider:
        # Meta Llama models
        body = json.dumps({
            "prompt": "Hello, what can you help me with today?",
            "max_gen_len": 100,
            "temperature": 0.5,
            "top_p": 0.9
        })
        print("Using Meta Llama format")
        
    else:
        # Generic fallback format
        body = json.dumps({
            "prompt": "Hello, what can you help me with today?",
            "max_tokens": 100,
            "temperature": 0.5
        })
        print(f"Using generic format for unknown provider: {model_provider}")
    
    # Make the API call
    try:
        print("Sending request to Bedrock...")
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )
        
        # Parse the response
        response_body = json.loads(response['Body'].read())
        print(f"\nResponse structure: {list(response_body.keys())}")
        
        # Extract and print the response based on model provider
        if "anthropic" in model_provider:
            output = response_body.get('content', [{}])[0].get('text', 'No response')
        elif "amazon" in model_provider:
            output = response_body.get('results', [{}])[0].get('outputText', 'No response')
        elif "ai21" in model_provider:
            output = response_body.get('completions', [{}])[0].get('data', {}).get('text', 'No response')
        elif "cohere" in model_provider:
            output = response_body.get('generations', [{}])[0].get('text', 'No response')
        elif "meta" in model_provider:
            output = response_body.get('generation', 'No response')
        else:
            # Generic fallback
            output = str(response_body)
        
        print("\nModel Response:")
        print("-" * 40)
        print(output)
        print("-" * 40)
        print("\nTest successful!")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTest failed.")
        return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get model ID from environment or use a default
    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-lite-v1")
    
    # Test the model
    success = test_model(model_id)
    
    # If failed with the environment variable model, try a different one
    if not success:
        print("\n\nFirst model test failed. Trying amazon.titan-text-lite-v1 instead...")
        test_model("amazon.titan-text-lite-v1")