pipeline {
    agent any
    environment {
        PATH = '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
    }
    stages {
        stage('static code analysis') {
            steps {
                sh '/usr/local/bin/pycodestyle --exclude=kube-virtualenv .'
            }
        }
        stage('setup') {
            steps {
                sh 'python3 -m venv kube-virtualenv'
	            sh '''
	                . kube-virtualenv/bin/activate
	                pip install -r requirements.txt
	            '''
                sh '''
                    cd ami/salt/certs
                    make
                '''
            }
        }
        stage('build amis') {
            steps {
                sh '''
                    cd ami
                    make
                '''
            }
        }
        stage('build cloudfoundation stack') {
            steps {
                sh '''
                    . kube-virtualenv/bin/activate
                    python stack.py delete
                    python stack.py create
                '''
            }
        }
        stage('test') {
            steps {
                sh '''
                    . kube-virtualenv/bin/activate
                    python run-tests.py
                '''
            }
        }
    }
    post {
        always {
            deleteDir()
        }
    }
}
