import json
import os
from datetime import datetime
from pathlib import Path
import random
import numpy as np

import torch
import tqdm
import shutil

#def cuda(x):
#    return x.cuda(async=True) if torch.cuda.is_available() else x


def write_event(filename, epoch, data):
    print("{0},{1:.4f},{2:.4f},{3:.4f},{4}".format(
                 epoch,data[0], data[1], data[2], int(data[3])), file=open(filename, "a"))


def save_checkpoint(state, is_best, filename):
    torch.save(state, filename)
    if is_best:
        print("saving the best model")
        shutil.copyfile(filename, str(filename).replace('last','best'))


def train(args, model, criterion, train_loader, valid_loader, validation, init_optimizer, epochs=None, num_classes=None):
    lr = args.lr
    n_epochs = epochs or args.epochs
    optimizer = init_optimizer(lr)

    root = Path(args.outputfolder)
    model_path_best = root / 'checkpoint_best.pth.tar'
    model_path_last = root / 'checkpoint_last.pth.tar'
    if model_path_best.exists():
        state = torch.load(str(model_path_best))
        epoch = state['epoch']
        step = state['step']
        best_accuracy = state['best_accuracy']
        model.load_state_dict(state['model'])
        print('Restored model, epoch {}, step {:,}, bets accuracy {}'.format(epoch, step, best_accuracy))
    else:
        epoch = 1
        step = 0
        best_accuracy = 0

    progress = root.joinpath('progress.txt')
    print("epoch,training_loss,val_loss,val_accuracy,is_best", file=open(progress, "w"))

    valid_losses = []
    for epoch in range(epoch, n_epochs + 1):
        model.train()
        random.seed()
        tq = tqdm.tqdm(total=(len(train_loader) * args.batch_size))
        tq.set_description('Epoch {}, lr {}'.format(epoch, lr))
        losses = []
        tl = train_loader
        try:
            mean_loss = 0
            for i, (inputs, targets) in enumerate(tl):
                inputs = cuda(inputs)
                with torch.no_grad():
                    targets = cuda(targets)
                #inputs, targets = variable(inputs), variable(targets)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                optimizer.zero_grad()
                batch_size = inputs.size(0)
                loss.backward()
                optimizer.step()
                step += 1
                tq.update(batch_size)
                losses.append(loss.item())
                mean_loss = np.mean(losses[-10:])
                tq.set_postfix(loss='{:.5f}'.format(mean_loss))
            tq.close()

            valid_metrics = validation(model, criterion, valid_loader, num_classes)
            valid_loss = valid_metrics['valid_loss']
            valid_accuracy = valid_metrics['valid_accuracy']
            valid_losses.append(valid_loss)

            is_best = valid_accuracy >= best_accuracy
            best_accuracy = max(valid_accuracy, best_accuracy)

            write_event(progress, epoch, [mean_loss, valid_loss, valid_accuracy, is_best])

            # upload progress
            if args.progress_upload_key:
                os.system('aws s3 cp '+str(progress)+' s3://pheno-test/'+args.progress_upload_key)

            save_checkpoint({
                'epoch': epoch + 1,
                'arch': args.model,
                'model': model.state_dict(),
                'best_accuracy': best_accuracy,
                'step': step,
            }, is_best, str(model_path_last))

        except KeyboardInterrupt:
            tq.close()
            print('done.')
            return
