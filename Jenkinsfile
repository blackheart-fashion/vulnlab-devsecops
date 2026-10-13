// =====================================================================
// Jenkinsfile — VulnLab DevSecOps CI/CD Pipeline
//
// This is NOT just a build-and-deploy pipeline — it's a teaching example
// of "shift-left security" in a DevOps pipeline:
//
//   Checkout -> Build -> [SAST] -> [Secret Scan] -> [Container Scan] ->
//   Deploy -> Smoke Test
//
// Each bracketed stage is an automated security gate — exactly the kind
// of thing a real DevSecOps pipeline runs BEFORE code reaches production.
// Students should notice: these scanners actually FIND several of the
// 20 intentional vulnerabilities automatically (hardcoded secret, shell
// injection pattern, etc.) — proving why these gates matter.
//
// Prerequisites on the Jenkins agent:
//   - Docker installed and Jenkins user has docker permissions
//     (add jenkins user to the docker group: usermod -aG docker jenkins)
//   - Port 5000 free on the agent (or change APP_PORT below)
// =====================================================================

pipeline {
    agent any

    environment {
        IMAGE_NAME   = "vulnlab"
        IMAGE_TAG    = "${env.BUILD_NUMBER}"
        CONTAINER    = "vulnlab_target"
        APP_PORT     = "5000"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        // -----------------------------------------------------------
        // CI stage 1: Source Control Checkout
        // -----------------------------------------------------------
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // -----------------------------------------------------------
        // CI stage 2: Build (Containerization)
        // -----------------------------------------------------------
        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest ."
            }
        }

        // -----------------------------------------------------------
        // DevSecOps Gate 1: SAST — Static Application Security Testing
        // Scans SOURCE CODE for insecure patterns before it ever runs.
        // -----------------------------------------------------------
        stage('SAST Scan (bandit)') {
            steps {
                sh '''
                    docker run --rm -v "$(pwd)":/src -w /src python:3.11-slim bash -c "
                        pip install --quiet bandit &&
                        bandit -r . -f txt -o bandit-report.txt || true
                    "
                '''
                archiveArtifacts artifacts: 'bandit-report.txt', allowEmptyArchive: true
            }
        }

        // -----------------------------------------------------------
        // DevSecOps Gate 2: Secret Scanning
        // Scans the GIT HISTORY and working tree for hardcoded secrets
        // (API keys, passwords, the hardcoded SECRET_KEY in app.py — vuln #20).
        // This is exactly the class of tool (gitleaks/truffleHog) real
        // pipelines run to stop secrets leaking into a repo.
        // -----------------------------------------------------------
        stage('Secret Scan (gitleaks)') {
            steps {
                sh '''
                    docker run --rm -v "$(pwd)":/repo zricethezav/gitleaks:latest \
                        detect --source=/repo --no-git -r /repo/gitleaks-report.json --exit-code 0 || true
                '''
                archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true
            }
        }

        // -----------------------------------------------------------
        // DevSecOps Gate 3: Container Image Scanning
        // Scans the BUILT IMAGE's OS packages + Python dependencies for
        // known CVEs. This is a core cloud/container-security practice —
        // every image pushed to a registry (ECR/ACR/GCR/Docker Hub) in a
        // real pipeline should pass through a scanner like this.
        // -----------------------------------------------------------
        stage('Container Image Scan (Trivy)') {
            steps {
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy:latest image --severity HIGH,CRITICAL \
                        --format table -o trivy-report.txt ${IMAGE_NAME}:latest || true
                '''
                archiveArtifacts artifacts: 'trivy-report.txt', allowEmptyArchive: true
            }
        }

        // -----------------------------------------------------------
        // CD stage 1: Tear down previous release (rolling deploy, single host)
        // -----------------------------------------------------------
        stage('Stop Previous Container') {
            steps {
                sh '''
                    docker rm -f ${CONTAINER} || true
                '''
            }
        }

        // -----------------------------------------------------------
        // CD stage 2: Deploy
        // In a real cloud pipeline this stage would instead push the
        // image to a registry (ECR/ACR/GCR) and trigger a rolling update
        // on ECS/AKS/GKE/Kubernetes. Here we deploy locally for the demo —
        // see DEVOPS_CLOUD_GUIDE.md for how to extend this to real cloud infra.
        // -----------------------------------------------------------
        stage('Deploy for Live Pentest Demo') {
            steps {
                sh '''
                    docker run -d \
                        --name ${CONTAINER} \
                        -p ${APP_PORT}:5000 \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:latest
                '''
            }
        }

        // -----------------------------------------------------------
        // CD stage 3: Post-deploy health verification (observability)
        // -----------------------------------------------------------
        stage('Smoke Test') {
            steps {
                sh '''
                    sleep 3
                    curl -f http://localhost:${APP_PORT}/healthz
                '''
            }
        }
    }

    post {
        success {
            echo "VulnLab deployed successfully. Demo URL: http://<jenkins-host>:${APP_PORT}/"
            echo "Review archived reports: bandit-report.txt, gitleaks-report.json, trivy-report.txt"
        }
        failure {
            echo "Pipeline failed — check console output above."
        }
    }
}
