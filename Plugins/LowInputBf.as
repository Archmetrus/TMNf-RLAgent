bool executeHandler = false;
SimulationState@ stateToRestore = null;
int nextCheck;
int iterationCount;
vec3 lastPos;
int bestFinishTime;
bool stopOnFinish;
bool findAllFinishes;
string resultFile;
bool saveWithTimestamp;
int timestampStartSearch;
int timeLimit;
int goalHeight;
float goalPosDiff;

void Main()
{
    RegisterVariable("lowinput_minTime", "Min Time for input change");
    RegisterVariable("lowinput_maxTime", "Max Time for run to finish");

    RegisterValidationHandler("low_input_bf", "Low Input BF");
}

void OnSimulationBegin(SimulationManager@ simManager)
{
    executeHandler = GetVariableString("controller") == "low_input_bf";
    if (!executeHandler) {
        // Not our handler, do nothing.
        return;
    }
    nextCheck = CurrentUpTimestamp() + 1000;
    iterationCount = 0;
    lastPos = vec3(0, 0, 0);
    bestFinishTime = -1;
    
    // Parameters that can be changed
    stopOnFinish = true;
    findAllFinishes = false;
    resultFile = "result";
    // saveWithTimestamp = true;
    
    // timestampStartSearch = 667320;
    // timestampStartSearch = 667000;
    // timestampStartSearch = 666000;
    timestampStartSearch = 121200; // 529000
    timeLimit = 743370; // for A01
    timestampStartSearch = GetVariableDouble("lowinput_minTime");
    timeLimit = GetVariableDouble("lowinput_maxTime");
    goalHeight = 9; // 9 fell in water or out of stadium, 24 fell off in A01, use trigger?
    goalPosDiff = 0.1;

    // A01 12:22.36 (750000 = 12:30:00)
    // 667320 press up (11:07.32)
    
    simManager.RemoveStateValidation();
    simManager.SetSimulationTimeLimit(timeLimit);

    print("Starting low input bf");
}

void OnSimulationStep(SimulationManager@ simManager, bool userCancelled)
{
    if (!executeHandler) {
        // Not our handler, do nothing.
        return;
    }
    if (userCancelled) {
        simManager.ForceFinish();
        return;
    }

    if (simManager.PlayerInfo.RaceFinished) {
        Accept(simManager);
        if (!stopOnFinish) {
            Reject(simManager); // keep searching for faster end after finding finish
            // return;
        }
    }

    int raceTime = simManager.RaceTime;
    // print("" + raceTime);
    if (raceTime == 0) {
        simManager.InputEvents.Clear(); // if the bruteforced replay has inputs
    }
    if (raceTime == CurrentUpTimestamp()) {
        @stateToRestore = simManager.SaveState(); // an input changed at the restoring timestamp will be applied
    }
    else if (raceTime == nextCheck) {
        // Check if the run is worth to simulate longer or not
        vec3 pos = simManager.Dyna.CurrentState.Location.Position;
        
        float posDiff = Math::Distance(pos, lastPos);
        bool wantReject = posDiff < goalPosDiff;
        wantReject = wantReject || pos.y < goalHeight;

        if (wantReject) {
            // print("pos=" + pos.ToString());
            Reject(simManager);
            return;
        } else {
            lastPos = pos;
            nextCheck += 1000;
        }
    }
    if (raceTime >= timeLimit - 10)
    {
        Reject(simManager);
    }
}

int CurrentUpTimestamp()
{
    return timestampStartSearch + iterationCount * 10;
}

void Reject(SimulationManager@ simManager)
{
    // print("iteration " + iterationCount);
    iterationCount++;

    if (CurrentUpTimestamp() >= timeLimit) {
        // an earlier iteration finished before this one starts, stop the bf
        simManager.ForceFinish();
    }

    simManager.InputEvents.Clear();
    simManager.InputEvents.Add(CurrentUpTimestamp(), InputType::Up, 1);
    simManager.RewindToState(stateToRestore);
    
    // new position after rewind
    lastPos = simManager.Dyna.CurrentState.Location.Position;
    nextCheck = CurrentUpTimestamp() + 1000;
    if (bestFinishTime == -1) {
        print("Trying press up " + simManager.RaceTime);
    } else {
        print("Trying press up " + simManager.RaceTime + ", bestFinishTime=" + bestFinishTime);
    }
}

void Accept(SimulationManager@ simManager)
{
    int finishTime = simManager.RaceTime;

    CommandList list;
    list.Content = simManager.InputEvents.ToCommandsText();
    
    if (bestFinishTime == -1 || finishTime < bestFinishTime) 
    {
        bestFinishTime = finishTime;
        if (!findAllFinishes) {
            // Speeds up the later runs because lowers timeLimit
            timeLimit = finishTime;
        }

        list.Save(resultFile + "_" + finishTime + ".txt");
        print("Run finished! Time: " + finishTime + ", " + list.Content + " saved in result.txt");
    } else {
        print("Run finished! But slower: " + finishTime + ">" + bestFinishTime + " with " + list.Content);
    }
}

void OnCheckpointCountChanged(SimulationManager@ simManager, int count, int target)
{
    if (!executeHandler) {
        // Not our handler, do nothing.
        return;
    }
    if (count == target) {
        // Keep simulation going if the replay finishes before the inputs
        simManager.PreventSimulationFinish();
    }
}

PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.Name = "LowInputBf";
    info.Author = "Shweetz";
    info.Version = "v1.0.0";
    info.Description = "Description";
    return info;
}
