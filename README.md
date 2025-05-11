# Competitive Programming & Technical Inteview Problem Note Uploader and Topic Recommender

This web application allows users to upload or type competitive programming notes and receive topic recommendations and summaries using AWS Bedrock. It integrates with Amazon S3 for note storage and uses Flask as the backend.

## Setup Instructions

### Prerequisites
- Python 3.8+
- AWS account with Bedrock access
- S3 bucket setup with appropriate permissions

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Lukas-L-Hu/AlgoNotes.git
   cd AlgoNotes

3. **Create a Virtual Environment**

   python -m venv venv
   source venv/bin/activate
   On Windows use `venv\Scripts\activate` or .\venv\Scripts\Activate.ps1

3. **Set Environment Variables in PowerShell**
   $Env:AWS_DEFAULT_REGION="YOUR REGION"

   $Env:AWS_ACCESS_KEY_ID="YOUR ACCESS KEY"

   $Env:AWS_SECRET_ACCESS_KEY="YOUR SECRET ACCESS KEY"

   $Env:AWS_SESSION_TOKEN="YOU SESSION TOKEN"

5. **Run Flask App**

   Run python app.py in the terminal

### Technologies Used

Frontend: HTML, CSS, JavaScript
Backend: Flask (Python)
Cloud Services: AWS S3 (for file storage), AWS Bedrock (for text generation / topic suggestion)

### Team Members and Contributions

Lukas L. Hu

- Flask backend integration with AWS S3
- Bedrock recommendation and summarization logic
- Frontend HTML/CSS design and JavaScript hooks
- GitHub repository setup and deployment
