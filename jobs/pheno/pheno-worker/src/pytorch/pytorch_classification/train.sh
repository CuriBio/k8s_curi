#!/bin/bash

display_usage() {
	echo -e "\nUsage:\n sh train.sh [config file] \n"
	}

if [  $# -le 0 ]
then
	display_usage
	exit 1
fi

################################################
config=$1
. ./$config

exp=${exp} #_${cell}_${drug}_${channel}_${time}
expFolder=/home/$USER/Experiments/$exp
inputFolder=$expFolder/data

# copy config file to expFolder
cp $config $expFolder/config_$exp.txt

# get config params
. $expFolder/config_$exp.txt

# set output paths
patchFolder=$expFolder/patches
augmentedPatchFolder=$expFolder/augmented_patches
outFolder=$expFolder/output


# output log file
logFilename=$expFolder/$exp.log

echo "training model -- "

# train model
if [ "$nohup" = true ]
then
	nohup python -u train_new.py $augmentedPatchFolder --outputfolder $outFolder \
	                                               --batch-size $batch_size \
												                         --arch $model  \
																								 --mode "regression" \
                                                       --checkpoint $initial_model_file \
                                                       --workers $workers \
                                                       --lr $learning_rate \
                                                       --epochs $epochs \
                                                       --precrop-size $precrop_size \
                                                       --max_iters_per_epoch $max_iters \
                                                       --log-file $logFilename  > $expFolder/training.log 2>&1 &
else
	python train_new.py $augmentedPatchFolder --outputfolder $outFolder \
	                                      --batch-size $batch_size \
                                              --arch $model  \
																							--mode "regression" \
                                              --checkpoint $initial_model_file \
                                              --workers $workers \
                                              --lr $learning_rate \
                                              --epochs $epochs \
                                              --precrop-size $precrop_size \
                                              --max_iters_per_epoch $max_iters \
                                              --log-file $logFilename

fi
