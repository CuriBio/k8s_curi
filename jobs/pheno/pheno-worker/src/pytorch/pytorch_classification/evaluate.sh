#!/bin/bash


display_usage() {
        echo -e "\nUsage:\n sh evaluate.sh [config file] \n"
        }

if [  $# -le 0 ]
then
        display_usage
        exit 1
fi


config=$1
. ./$config

exp=${exp} #_${cell}_${drug}_${channel}_${time}


expFolder=/home/$USER/Experiments/$exp

# get config params
. $expFolder/config_$exp.txt

# set output paths
inputFolder=$expFolder/data
patchFolder=$expFolder/data_patches
outFolder=$expFolder/output

# output log file
logFilename=$expFolder/${exp}_eval.log

echo "evaluating performance of classification net on images -- "
# evaluate performance - train
python evaluateImageFolderRegression.py $inputFolder/Train --outputfile $outFolder/evaluate_train.csv \
                              --arch $model \
			                        --mode "regression" \
			                        --checkpoint $outFolder/model_best.pth.tar \
		                          --precrop-size $precrop_size \
                              --patch_rows $nPatch_w \
                              --patch_cols $nPatch_h \
                              --noscale $noscale \
                              --trainorval "Train" \
   			                      --convert2gray $convert2gray \
			                        --log-file $logFilename

# evaluate performance - val
python evaluateImageFolderRegression.py $inputFolder/Val --outputfile $outFolder/evaluate_val.csv \
                              --arch $model \
			                        --mode "regression" \
			                        --checkpoint $outFolder/model_best.pth.tar \
			                        --precrop-size $precrop_size \
                              --patch_rows $nPatch_w \
                              --patch_cols $nPatch_h \
                              --noscale $noscale \
                              --trainorval "Val" \
 			                        --convert2gray $convert2gray \
			                        --log-file $logFilename
