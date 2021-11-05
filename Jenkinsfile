node('linux') {
    stage('Checkout') {
        cleanWs()
        checkout scm
    }

    stage('Clean') {
        sh 'make clean'
    }

    stage('Build image and start container') {
        sh 'make container'
    }

    stage('License info') {
        warnError('Error occurred, continue to next stage.') {
            sh 'make licenses'
            archiveArtifacts artifacts: 'licenses.csv, licenses.confluence'
        }
    }

    stage('Docs') {
        sh 'make docs html'
        archiveArtifacts artifacts: 'docs/sphinx-build-html.log'
        recordIssues(tools: [sphinxBuild(name: 'Docs',
                                         pattern: 'docs/sphinx-build-html.log',
                                         reportEncoding: 'UTF-8')])
        publishHTML([allowMissing: false,
                     alwaysLinkToLastBuild: true,
                     keepAll: false,
                     reportDir: '',
                     reportFiles: 'docs/_build/html/index.html',
                     reportName: 'Doxygen',
                     reportTitles: ''])
    }

    stage('Linting') {
        warnError('Error occurred, continue to next stage.') {
            try {
                sh 'make pylint'
            } finally {
                archiveArtifacts artifacts: 'pylint.log'
                recordIssues(tools: [pyLint(name: 'Linting',
                                            pattern: 'pylint.log')])
            }
        }
    }

    stage('Style') {
        warnError('Error occurred, continue to next stage.') {
            try {
                sh 'make pycodestyle'
            } finally {
                archiveArtifacts artifacts: 'pycodestyle.log'
                recordIssues(tools: [pep8(name: 'Style',
                                          pattern: 'pycodestyle.log')])
            }
        }
    }

    stage('Tests') {
        warnError('Error occurred, continue to next stage.') {
            try {
                // After timeout test will be aborted, thus there won't
                // be any artifacts generated
                timeout(unit: 'MINUTES', time: 5) {
                    sh 'make test'
                }
            } finally {
                archiveArtifacts artifacts: '.coverage, coverage.xml, testreport.xml'
                junit 'testreport.xml'
                cobertura autoUpdateHealth: false,
                autoUpdateStability: false,
                coberturaReportFile: 'coverage.xml',
                conditionalCoverageTargets: '70, 0, 0',
                failUnhealthy: false,
                failUnstable: false,
                lineCoverageTargets: '80, 0, 0',
                maxNumberOfBuilds: 0,
                methodCoverageTargets: '80, 0, 0',
                onlyStable: false,
                sourceEncoding: 'ASCII',
                zoomCoverageChart: false
            }
        }
    }

    stage('Stop container') {
        sh 'make stop-container'
    }
}
