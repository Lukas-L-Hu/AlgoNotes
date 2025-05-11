import os
import json
import boto3
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Check if credentials exist
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_session_token = os.getenv("AWS_SESSION_TOKEN")
s3_bucket_name = os.getenv('S3_BUCKET_NAME')
bedrock_model_id = os.getenv('BEDROCK_MODEL_ID')
region = os.getenv('AWS_REGION')

# Print credentials availability (not the actual values for security)
print(f"AWS Access Key available: {bool(aws_access_key)}")
print(f"AWS Secret Key available: {bool(aws_secret_key)}")
print(f"AWS Session Token available: {bool(aws_session_token)}")
print(f"S3 Bucket Name: {s3_bucket_name}")
print(f"Bedrock Model ID: {bedrock_model_id}")
print(f"AWS Region: {region}")

app = Flask(__name__)
CORS(app)

# Only create clients if credentials are available
if aws_access_key and aws_secret_key and region:
    try:
        s3 = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token
        )
        
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token
        )
        print("AWS clients created successfully")
    except Exception as e:
        print(f"Error creating AWS clients: {e}")
        traceback.print_exc()
else:
    print("WARNING: AWS credentials not available. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION environment variables.")
    s3 = None
    bedrock_runtime = None

# Upload raw text as a .txt file to S3
@app.route('/api/submit-note', methods=['POST'])
def submit_note():
    if not s3:
        return jsonify({"error": "AWS credentials not configured"}), 500
        
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({"error": "No content provided"}), 400

    file_name = f"{uuid.uuid4()}.txt"
    try:
        s3.put_object(Bucket=s3_bucket_name, Key=file_name, Body=content)
        return jsonify({"message": "Note submitted successfully"})
    except Exception as e:
        print(f"Error submitting note: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Upload a file to S3
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if not s3:
        return jsonify({"error": "AWS credentials not configured"}), 500
        
    file = request.files.get('file')
    if not file or not file.filename.endswith('.txt'):
        return jsonify({"error": "Only .txt files are allowed"}), 400

    try:
        s3.upload_fileobj(file, s3_bucket_name, file.filename)
        return jsonify({"message": "File uploaded successfully"})
    except Exception as e:
        print(f"Error uploading file: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if not s3:
        return jsonify({"error": "AWS credentials not configured for S3"}), 500

    try:
        # Fetch notes from S3
        response = s3.list_objects_v2(Bucket=s3_bucket_name)
        contents = []

        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.txt'):
                s3_obj = s3.get_object(Bucket=s3_bucket_name, Key=obj['Key'])
                contents.append(s3_obj['Body'].read().decode('utf-8'))

        if not contents:
            return jsonify({"error": "No content found in S3"}), 404

        joined_text = "\n\n".join(contents)

        if not bedrock_runtime:
            return jsonify({
                "warning": "Bedrock access not configured. Returning raw notes.",
                "notes": contents
            })

        model_provider = bedrock_model_id.split('.')[0].lower()
        prompt = f"Summarize the following notes in a clear and concise way:\n\n{joined_text}"

        # Prepare request body depending on model
        if "anthropic" in model_provider:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5
            })
        elif "amazon" in model_provider:
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.5,
                    "topP": 0.9
                }
            })
        elif "ai21" in model_provider:
            body = json.dumps({
                "prompt": prompt,
                "maxTokens": 1000,
                "temperature": 0.5,
                "topP": 0.9
            })
        elif "cohere" in model_provider:
            body = json.dumps({
                "prompt": prompt,
                "max_tokens": 1000,
                "temperature": 0.5
            })
        elif "meta" in model_provider:
            body = json.dumps({
                "prompt": prompt,
                "max_gen_len": 1000,
                "temperature": 0.5,
                "top_p": 0.9
            })
        else:
            body = json.dumps({
                "prompt": prompt,
                "max_tokens": 1000,
                "temperature": 0.5
            })

        response = bedrock_runtime.invoke_model(
            modelId=bedrock_model_id,
            body=body
        )
        response_stream = response.get('body') or response.get('Body')
        response_body = json.loads(response_stream.read())

        if "anthropic" in model_provider:
            summary = response_body.get('content', [{}])[0].get('text', 'No summary provided')
        elif "amazon" in model_provider:
            summary = response_body.get('results', [{}])[0].get('outputText', 'No summary provided')
        elif "ai21" in model_provider:
            summary = response_body.get('completions', [{}])[0].get('data', {}).get('text', 'No summary provided')
        elif "cohere" in model_provider:
            summary = response_body.get('text', 'No summary provided')
        elif "meta" in model_provider:
            summary = response_body.get('generation', 'No summary provided')
        else:
            summary = str(response_body)

        return jsonify({"summary": summary})

    except Exception as e:
        print(f"Error generating summary: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Get topic recommendations from notes in S3
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    if not s3:
        return jsonify({"error": "AWS credentials not configured for S3"}), 500
        
    try:
        # First fetch content from S3
        print(f"Listing objects from bucket: {s3_bucket_name}")
        response = s3.list_objects_v2(Bucket=s3_bucket_name)
        contents = []

        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.txt'):
                s3_obj = s3.get_object(Bucket=s3_bucket_name, Key=obj['Key'])
                contents.append(s3_obj['Body'].read().decode('utf-8'))

        if not contents:
            return jsonify({"error": "No content found in S3"}), 404

        joined_text = "\n\n".join(contents)
        
        # Now try to use Bedrock if available
        if not bedrock_runtime:
            # Fallback to returning raw content if Bedrock not available
            return jsonify({
                "warning": "Bedrock access not configured or unavailable. Returning raw notes instead.",
                "notes": contents
            })
            
        try:
            # Create request body based on model provider
            print(f"Preparing request for model: {bedrock_model_id}")
            model_provider = bedrock_model_id.split('.')[0].lower()
            
            if "anthropic" in model_provider:
                # Claude models (anthropic.claude-*)
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}"
                        }
                    ],
                    "temperature": 0.5
                })
                print("Using Anthropic Claude format")
                
            elif "amazon" in model_provider:
                # Amazon Titan models (amazon.titan-*)
                body = json.dumps({
                    "inputText": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}",
                    "textGenerationConfig": {
                        "maxTokenCount": 1000,
                        "temperature": 0.5,
                        "topP": 0.9
                    }
                })
                print("Using Amazon Titan format")
                
            elif "ai21" in model_provider:
                # AI21 Jurassic models (ai21.j2-*)
                body = json.dumps({
                    "prompt": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}",
                    "maxTokens": 1000,
                    "temperature": 0.5,
                    "topP": 0.9
                })
                print("Using AI21 format")
                
            elif "cohere" in model_provider:
                # Cohere models (cohere.command-*)
                body = json.dumps({
                    "prompt": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}",
                    "max_tokens": 1000,
                    "temperature": 0.5
                })
                print("Using Cohere format")
                
            elif "meta" in model_provider:
                # Meta Llama models (meta.llama-*)
                body = json.dumps({
                    "prompt": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}",
                    "max_gen_len": 1000,
                    "temperature": 0.5,
                    "top_p": 0.9
                })
                print("Using Meta Llama format")
                
            else:
                # Generic fallback format
                body = json.dumps({
                    "prompt": f"Based on these notes, what are the next topics I should study?\n\n{joined_text}",
                    "max_tokens": 1000,
                    "temperature": 0.5
                })
                print(f"Using generic format for unknown provider: {model_provider}")

            print(f"Calling Bedrock model: {bedrock_model_id}")
            response = bedrock_runtime.invoke_model(
                modelId=bedrock_model_id,
                body=body,
            )
            
            try:
                response_stream = response.get('body') or response.get('Body')
                if response_stream:
                    response_body = json.loads(response_stream.read())
                else:
                    raise ValueError(f"No 'Body' or 'body' in response: {response}")
            except Exception as e:
                print(f"Failed to parse Bedrock response: {e}")
                print(f"Raw response: {response}")
                raise

            print(f"Response structure: {list(response_body.keys())}")
            
            # Extract recommendation based on model provider
            if "anthropic" in model_provider:
                recommendation = response_body.get('content', [{}])[0].get('text', 'No recommendation provided')
            elif "amazon" in model_provider:
                recommendation = response_body.get('results', [{}])[0].get('outputText', 'No recommendation provided')
            elif "ai21" in model_provider:
                recommendation = response_body.get('completions', [{}])[0].get('data', {}).get('text', 'No recommendation provided')
            elif "cohere" in model_provider:
                recommendation = response_body.get('text', 'No recommendation provided')
            elif "meta" in model_provider:
                recommendation = response_body.get('generation', 'No recommendation provided')
            else:
                # Generic fallback
                recommendation = str(response_body)
                
            return jsonify({"recommendation": recommendation})
            
        except Exception as e:
            print(f"Error calling Bedrock: {e}")
            traceback.print_exc()
            
            # For debugging: print the model ID and request body
            print(f"Failed model ID: {bedrock_model_id}")
            print(f"Request body sample (first 100 chars): {body[:100]}...")
            
            return jsonify({
                "warning": f"Error using Bedrock model: {str(e)}",
                "notes": contents,
                "modelId": bedrock_model_id
            })

    except Exception as e:
        print(f"Error in recommendations: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Serve frontend
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/check-config', methods=['GET'])
def check_config():
    """Endpoint to check if AWS configuration is working"""
    config_status = {
        "s3": {"configured": False, "message": "Not initialized"},
        "bedrock": {"configured": False, "message": "Not initialized"},
        "region": region
    }
    
    # Check S3 configuration
    if s3:
        try:
            s3.list_buckets()
            config_status["s3"] = {
                "configured": True,
                "message": "S3 access confirmed",
                "bucket": s3_bucket_name
            }
        except Exception as e:
            config_status["s3"] = {
                "configured": False,
                "message": f"S3 error: {str(e)}"
            }
    
    # Check Bedrock configuration
    if bedrock_runtime:
        try:
            # List available models
            bedrock_client = boto3.client(
                'bedrock',
                region_name=region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                aws_session_token=aws_session_token
            )
            
            # Try listing foundation models
            try:
                models = bedrock_client.list_foundation_models()
                available_models = [model['modelId'] for model in models.get('modelSummaries', [])]
                
                config_status["bedrock"] = {
                    "configured": True,
                    "message": "Bedrock access confirmed",
                    "requested_model": bedrock_model_id,
                    "available_models": available_models,
                    "model_access": bedrock_model_id in available_models
                }
            except Exception as e:
                # Fallback to just checking if the specific model is accessible
                try:
                    bedrock_runtime.invoke_model(
                        modelId=bedrock_model_id,
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 10,
                            "messages": [{"role": "user", "content": "Hello"}],
                            "temperature": 0.5
                        })
                    )
                    config_status["bedrock"] = {
                        "configured": True,
                        "message": "Bedrock model access confirmed",
                        "model": bedrock_model_id
                    }
                except Exception as model_error:
                    config_status["bedrock"] = {
                        "configured": False,
                        "message": f"Bedrock model error: {str(model_error)}",
                        "model": bedrock_model_id
                    }
        except Exception as e:
            config_status["bedrock"] = {
                "configured": False,
                "message": f"Bedrock error: {str(e)}"
            }
    
    return jsonify(config_status)

if __name__ == '__main__':
    app.run(debug=True)