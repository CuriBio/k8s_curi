#!/bin/bash

display_usage() {
	echo -e "\nUsage:\n sh run.sh [config file] \n"
	}

if [  $# -le 0 ]
then
	display_usage
	exit 1
fi


config=$1
. ./$config

expFolder=/home/$USER/Experiments/$exp
inputFolder=$expFolder/data

# copy config file to expFolder
cp $config $expFolder/config_$exp.txt

# get config params
. $expFolder/config_$exp.txt

# set output paths
patchFolder=$expFolder/patches
################################################ CORRECT THID
augmentedPatchFolder=$expFolder/augmented_patches
outFolder=$expFolder/output


# output log file
logFilename=$expFolder/$exp.log


mkdir -p $outFolder
if [ "$finetune" = true ]
then
   #copy the initial net to output folder
   finetuneFromFolder=/home/$USER/Experiments/$finetune_exp
   cp $finetuneFromFolder/output/checkpoint_best.pth.tar $outFolder/
fi

echo "training model -- "
# train model
if [ "$nohup" = true ]
then
	nohup python -u trainseg.py $augmentedPatchFolder --outputfolder $outFolder \
	                                         -c $center_crop \
						--device-ids $device_ids \
						--batch-size $batch_size \
						--model $model  \
						--workers $workers \
						--lr $learning_rate \
						--epochs $epochs \
						--jaccard-weight 1 \
						--labels $labels \
						--log-file $logFilename > $expFolder/training.log 2>&1 &
else
	python trainseg.py $augmentedPatchFolder --outputfolder $outFolder \
						-c $center_crop \
						--device-ids $device_ids \
						--batch-size $batch_size \
						--model $model  \
						--workers $workers \
						--lr $learning_rate \
						--epochs $epochs \
						--jaccard-weight 1 \
						--labels $labels \
						--log-file $logFilename
fi
