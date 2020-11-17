node {
    def buildMessage = null
    def is_deploy_branch = (env.BRANCH_NAME == "release" || env.BRANCH_NAME == "master")
    try {
        load "${DMAKE_JENKINS_FILE}"
        currentBuild.result = 'SUCCESS'
    } catch (e) {
        def abortedCauseDescription = getCauseDescriptionIfAborted()
        if (abortedCauseDescription) {
            currentBuild.result = 'ABORTED'
            buildMessage = abortedCauseDescription
        } else {
            currentBuild.result = 'FAILURE'
        }
        throw e
    } finally {
        if (is_deploy_branch) {
            notifyBuild("deepomatic-cli", currentBuild.result, buildMessage)
        }
    }
}

def notifyBuild(String channel, String buildStatus, String buildMessage) {
    if (buildStatus == 'SUCCESS') {
        color = '#36A64F' // green
    } else if (buildStatus == 'ABORTED') {
        color = '#ABABAB' // grey
    } else {
        color = '#D00000' // red
    }
    def message = "${buildStatus}"
    if (buildMessage) {
        message += " (${buildMessage})"
    }
    message += ": Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})"
    slackSend (color: color, message: message, botUser: true, channel: channel)
}

@NonCPS
def getCauseDescriptionIfAborted() {
    def action = manager.build.getAction(InterruptedBuildAction.class)
    if (action) {
        for (cause in action.causes) {
            if (cause instanceof jenkins.model.CauseOfInterruption.UserInterruption) {
                return cause.getShortDescription()
            }
        }
    }
}