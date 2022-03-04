#!/bin/bash
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
trainOutFilename=$expFolder/${exp}_eval_train_ionpath.csv
valOutFilename=$expFolder/${exp}_eval_val_ionpath.csv


if [ "$segment_image" = true ]
then

echo "segmenting images -- "
# segment images - train
python segmentImageFolder.py --data $inputFolder/Train/IMG --output_path $inputFolder/Train/PRED \
                            --model_type=$model \
							--model_path $outFolder \
							--batch-size $batch_size \
							--workers $workers  \
                            --labels $labels \
							--patch-rows $nPatch_w \
							--patch-cols $nPatch_h \
							--output_mask_type $output_mask_type \
							--log-file $logFilename


# segment images - val
python segmentImageFolder.py --data $inputFolder/Val/IMG --output_path $inputFolder/Val/PRED \
                                                         --model_type=$model \
                                                         --model_path $outFolder \
                                                         --batch-size $batch_size \
                                                         --workers $workers  \
                                                         --labels $labels \
                                                         --patch-rows $nPatch_w \
                                                         --patch-cols $nPatch_h \
                                                         --output_mask_type $output_mask_type \
                                                         --log-file $logFilename

fi


# evaluate images - train
IFS=',';for ch_name in `echo "$listofchannels"`;do
  substring=.$ch_name.
  python evaluate_per_channel.py --true_path $inputFolder/Train/LABEL \
  								--pred_path $inputFolder/Train/PRED \
								--orig_path $inputFolder/Train/IMG \
								--acceptable_noise 50 \
								--sub_string $substring \
								--outputfile $trainOutFilename
done



# evaluate images - val
IFS=',';for ch_name in `echo "$listofchannels"`;do
  substring=.$ch_name.
  python evaluate_per_channel.py --true_path $inputFolder/Val/LABEL \
                   --pred_path $inputFolder/Val/PRED \
				   --orig_path $inputFolder/Val/IMG \
				   --acceptable_noise 50 \
				   --sub_string $substring \
				   --outputfile $valOutFilename
done
