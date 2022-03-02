#!/bin/bash

display_usage() {
	echo -e "\nUsage:\n sh patchaugment.sh [config file] \n"
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
cp $config $expFolder/config_${exp}.txt

# get config params
. $expFolder/config_$exp.txt

# set output paths
patchFolder=$expFolder/patches
augmentedPatchFolder=$expFolder/augmented_patches
outFolder=$expFolder/output


# output log file
logFilename=$expFolder/${exp}_patch.log

if [ "$patch" = true ]
then
echo "generating patches -- "
# patch dataset - Train
python patchImageFolder.py $inputFolder/Train/IMG --outputfolder $patchFolder/Train \
                           --patches-rows $nPatch_h \
                           --patches-cols $nPatch_w \
                           --patch-size $patch_size \
                           --workers $workers \
                           --noscale $noscale \
                           --excludeNeg $excludeNeg \
                           --log-file $logFilename

# patch dataset - Val
python patchImageFolder.py $inputFolder/Val/IMG --outputfolder $patchFolder/Val \
							--patches-rows $nPatch_h \
							--patches-cols $nPatch_w \
							--patch-size $patch_size \
							--workers $workers \
							--noscale $noscale \
                                                        --excludeNeg $excludeNeg \
							--log-file $logFilename

fi

if [ "$augment" = true ]
then

echo "augmenting patches -- "
# augment patches - Train
python augment.py $patchFolder/Train/IMG --outputfolder $augmentedPatchFolder/Train/IMG \
			                 --log-file $logFilename

# augment patches - Val
python augment.py $patchFolder/Val/IMG --outputfolder $augmentedPatchFolder/Val/IMG \
				       --log-file $logFilename
fi
