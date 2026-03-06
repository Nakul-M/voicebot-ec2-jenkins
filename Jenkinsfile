pipeline {
    agent any

    environment {
        OLLAMA_HOST = "http://127.0.0.1:11434"
    }

    stages {

        stage('Clone Repository') {
            steps {
                git branch: 'main', url: 'https://github.com/Nakul-M/voicebot-ec2-jenkins.git'
            }
        }

        stage('Setup Python Environment') {
            steps {
                sh '''
                python3 -m venv venv
                source venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Start Ollama') {
            steps {
                sh '''
                nohup ollama serve > ollama.log 2>&1 &
                sleep 5
                '''
            }
        }

        stage('Pull Ollama Model') {
            steps {
                sh '''
                ollama pull gemma3:1b
                '''
            }
        }

        stage('Run Voicebot') {
            steps {
                sh '''
                source venv/bin/activate
                python src/app.py
                '''
            }
        }

    }

    post {
        success {
            echo 'Voicebot started successfully'
        }
        failure {
            echo 'Pipeline failed'
        }
    }
}