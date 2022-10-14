#!/bin/bash
#source activate pytorch_p36
#input
exp=$1

expFolder=/home/$USER/Experiments/$exp

# get config params
. $expFolder/config_$exp.txt

# set output paths
inputFolder=$expFolder/data
patchFolder=$expFolder/patches
augmentedPatchFolder=$expFolder/augmented_patches
outFolder=$expFolder/output

# output log file
logFilename=$expFolder/${exp}_eval.log


echo "segmenting patches -- "
# segment images - train
python segmentPatchFolder.py --data $patchFolder/Train/IMG --output_path $patchFolder/Train/PRED \
                            --model_type=$model \
							--model_path $outFolder \
							--batch-size $batch_size \
							--workers $workers  \
                            --labels $labels \
							--log-file $logFilename
# evaluate images - train
python evaluate.py --true_path $patchFolder/Train/LABEL \
				   --pred_path $patchFolder/Train/PRED \
				   --acceptable_noise 20 \
                                   --labels $labels \
				   --log-file $logFilename


# segment images - val
python segmentPatchFolder.py --data $patchFolder/Val/IMG --output_path $patchFolder/Val/PRED \
                                                         --model_type=$model \
                                                         --model_path $outFolder \
                                                         --batch-size $batch_size \
                                                         --workers $workers  \
                                                         --labels $labels \
							 --log-file $logFilename
# evaluate images - val
python evaluate.py --true_path $patchFolder/Val/LABEL \
				   --pred_path $patchFolder/Val/PRED \
				   --acceptable_noise 20 \
                                   --labels $labels \
				   --log-file $logFilename

