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

echo "classifying images -- "
# segment images - train
python classifyImageFolder.py $imageFolder --output_path $outFolder \
                                                 --arch=$model \
					                             --checkpoint $expFolder/output/model_best.pth.tar \
                                                 --num-classes $num_classes \
                                                 --precrop-size $precrop_size \
						                         --patch-rows $nPatch_w \
						                         --patch-cols $nPatch_h \
                                                 --noscale $noscale \
                      						     --convert2gray $convert2gray \
					                             --log-file $logFilename
