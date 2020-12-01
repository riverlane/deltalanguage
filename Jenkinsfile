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
        sh 'make docs epub'
        archiveArtifacts artifacts: 'docs/sphinx-build-html.log, docs/sphinx-build-epub.log'
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
            sh 'make pylint'
            archiveArtifacts artifacts: 'pylint.log'
            recordIssues(tools: [pyLint(name: 'Linting',
                                        pattern: 'pylint.log')])
        }
    }

    stage('Style') {
        warnError('Error occurred, continue to next stage.') {
            sh 'make pycodestyle'
            archiveArtifacts artifacts: 'pycodestyle.log'
            recordIssues(tools: [pep8(name: 'Style',
                                pattern: 'pycodestyle.log')])
        }
    }

    stage('Tests') {
        warnError('Error occurred, continue to next stage.') {
            sh 'make test'

            archiveArtifacts artifacts: '.coverage, coverage.xml, nosetests.xml'

            junit 'nosetests.xml'

            cobertura autoUpdateHealth: false,
            autoUpdateStability: false,
            coberturaReportFile: 'coverage.xml',
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

    stage('Clean container') {
        sh 'make clean-container'
    }
}
