#!/bin/bash
#source activate pytorch_p36
#input
imageFolder=$1
outFolder=$2
exp=$3

expFolder=/home/$USER/Experiments/$exp

# get config params
. $expFolder/config_$exp.txt

# make output folder
mkdir -p $outFolder

# output log file
logFilename=$outFolder/${exp}_deploy.log

echo "segmenting images -- "
# segment images - train
python segmentImageFolder.py --data $imageFolder --output_path $outFolder \
                                                 --model_type=$model \
												 --model_path $expFolder/output \
												 --batch-size $batch_size \
												 --workers $workers  \
                                                 --labels $labels \
												 --patch-rows $nPatch_w \
												 --patch-cols $nPatch_h \
												 --output_mask_type $output_mask_type \
												 --log-file $logFilename
