#!/bin/bash


. ./config.txt

dstFolder=/home/$USER/Experiments/$exp
mkdir -p $dstFolder

# copy config file to dstFolder
cp ./config.txt $dstFolder/config_$exp.txt

# get config params
. $dstFolder/config_$exp.txt

rootdir=$rootdir
listofchannels=$listofchannels

mkdir -p $dstFolder/data/Train/IMG
mkdir -p $dstFolder/data/Val/IMG
mkdir -p $dstFolder/data/Train/LABEL
mkdir -p $dstFolder/data/Val/LABEL

if [ "$make_labels" = true ]
then
        echo "making the masks of denosied images for training data" 
	python make_labels_ionpath.py $rootdir/denoised/Train/ $rootdir/denoised_mask/Train/
        echo "making the masks of denoised images for validation data"
	python make_labels_ionpath.py $rootdir/denoised/Val/ $rootdir/denoised_mask/Val/
fi

echo $listofchannels
IFS=',';for ch_name in `echo "$listofchannels"`;do
        echo $ch_name
	    cp $rootdir/original/Train/*.$ch_name.* $dstFolder/data/Train/IMG/
        cp $rootdir/original/Val/*.$ch_name.* $dstFolder/data/Val/IMG/
        cp $rootdir/denoised_mask/Train/*.$ch_name.* $dstFolder/data/Train/LABEL/
        cp $rootdir/denoised_mask/Val/*.$ch_name.* $dstFolder/data/Val/LABEL/

done
