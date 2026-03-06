pipeline {
    agent any

    environment {
        OLLAMA_HOST = "http://127.0.0.1:11434"
    }

    stages {

        stage('Clone Repository') {
            steps {
                echo "Cloning repository..."
                git branch: 'main', url: 'https://github.com/Nakul-M/voicebot-ec2-jenkins.git'
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo "Setting up Python virtual environment..."
                sh '''
                python3 -m venv venv
                source venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Verify Ollama Installation') {
            steps {
                echo "Checking Ollama installation..."
                sh '''
                if ! command -v ollama &> /dev/null
                then
                    echo "Ollama not installed. Installing..."
                    curl -fsSL https://ollama.com/install.sh | sh
                else
                    echo "Ollama already installed."
                fi
                '''
            }
        }

        stage('Start Ollama Server') {
            steps {
                echo "Starting Ollama server..."
                sh '''
                if ! pgrep -x "ollama" > /dev/null
                then
                    nohup ollama serve > ollama.log 2>&1 &
                    sleep 5
                else
                    echo "Ollama already running"
                fi
                '''
            }
        }

        stage('Pull AI Model') {
            steps {
                echo "Pulling Gemma model..."
                sh '''
                ollama pull gemma3:1b
                '''
            }
        }

        stage('Run Voicebot') {
            steps {
                echo "Starting voicebot..."
                sh '''
                chmod +x scripts/run.sh
                ./scripts/run.sh
                '''
            }
        }
    }

    post {

        success {
            echo "Voicebot deployed successfully!"
        }

        failure {
            echo "Pipeline failed!"
        }

        always {
            echo "Pipeline execution finished."
        }
    }
}