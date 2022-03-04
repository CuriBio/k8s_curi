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


echo "segmenting images -- "
# segment images - train
python segmentImageFolder.py --data $inputFolder/Train/IMG --output_path $inputFolder/Train/PRED \
                            --model_type=$model \
							--model_path $outFolder \
							--batch-size $batch_size \
							--workers $workers  \
                            --labels $labels \
							--patch-rows $nPatch_h \
							--patch-cols $nPatch_w \
							--output_mask_type $output_mask_type \
							--log-file $logFilename
# evaluate images - train
python evaluate.py --true_path $inputFolder/Train/LABEL \
				   --pred_path $inputFolder/Train/PRED \
				   --acceptable_noise 20 \
                                   --labels $labels \
				   --log-file $logFilename


# segment images - val
python segmentImageFolder.py --data $inputFolder/Val/IMG --output_path $inputFolder/Val/PRED \
                                                         --model_type=$model \
                                                         --model_path $outFolder \
                                                         --batch-size $batch_size \
                                                         --workers $workers  \
                                                         --labels $labels \
                                                         --patch-rows $nPatch_h \
							 --patch-cols $nPatch_w \
							 --output_mask_type $output_mask_type \
							 --log-file $logFilename
# evaluate images - val
python evaluate.py --true_path $inputFolder/Val/LABEL \
				   --pred_path $inputFolder/Val/PRED \
				   --acceptable_noise 20 \
                                   --labels $labels \
				   --log-file $logFilename
 
