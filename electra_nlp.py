# -*- coding: utf-8 -*-
"""Electra_NLP.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1XaFA86OkXCLoDPfgv6PbtkELKUY81ZJ1

#Installation package
"""

!pip uninstall -y transformers accelerate torch
!pip install transformers[torch] accelerate --upgrade
!pip install torch --upgrade
!pip install sentencepiece
!pip install datasets
!pip install evaluate
!pip install accelerate -U
!pip install transformers[torch] -U

!pip install evaluate

gpu_info = !nvidia-smi
gpu_info = '\n'.join(gpu_info)
if gpu_info.find('failed') >= 0:
  print('Not connected to a GPU')
else:
  print(gpu_info)

import torch

if torch.cuda.is_available():
    print("GPU is available")
    print(f"Device name: {torch.cuda.get_device_name(0)}")
else:
    print("GPU is not available")

"""#Import de Electra"""

from transformers import ElectraTokenizer, ElectraForSequenceClassification

# Spécifiez le modèle ELECTRA de petite taille
electra_model_name = "google/electra-small-discriminator"

# Téléchargez et chargez le tokenizer et le modèle
electra_tokenizer = ElectraTokenizer.from_pretrained(electra_model_name)
electra_model = ElectraForSequenceClassification.from_pretrained(electra_model_name)

# Définir le modèle en mode évaluation
electra_model.eval()

"""#Import de Bert

"""

from transformers import BertTokenizer, BertForSequenceClassification

# Spécifiez le modèle BERT de petite taille
bert_model_name = "prajjwal1/bert-small"

# Téléchargez et chargez le tokenizer et le modèle
bert_tokenizer = BertTokenizer.from_pretrained(bert_model_name)
bert_model = BertForSequenceClassification.from_pretrained(bert_model_name)

# Définir le modèle en mode évaluation
bert_model.eval()

"""#Import de Llama - ne pas utiliser."""

from transformers import AutoTokenizer, AutoModelForCausalLM

# Spécifiez un modèle de petite taille
llama_model_name = "distilgpt2"

# Téléchargez et chargez le tokenizer et le modèle
llama_tokenizer = AutoTokenizer.from_pretrained(llama_model_name)
llama_model = AutoModelForCausalLM.from_pretrained(llama_model_name)

# Définir le modèle en mode évaluation
llama_model.eval()

"""#Nombre de paramètres"""

def print_trainable_parameters(model):
    """
    Prints the number of trainable parameters in the model.
    """
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param:.2f}%"
    )

# Imprimer les paramètres
print("ELECTRA Model:")
print_trainable_parameters(electra_model)
print("BERT Model:")
print_trainable_parameters(bert_model)
print("LLaMA Model:")
print_trainable_parameters(llama_model)

"""#Benchmark 1 - classification de sentiments - en cours"""

from datasets import load_dataset

dataset = load_dataset("glue", "sst2")

from transformers import Trainer, TrainingArguments

def fine_tune_model(model, tokenizer, dataset, max_length=128):
    def preprocess_function(examples):
        return tokenizer(examples['sentence'], truncation=True, padding='max_length', max_length=max_length)

    encoded_dataset = dataset.map(preprocess_function, batched=True)

    training_args = TrainingArguments(
        output_dir='./results',
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        weight_decay=0.01,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=encoded_dataset['train'],
        eval_dataset=encoded_dataset['validation'],
    )

    trainer.train()
    return trainer

# Fine-tuning ELECTRA
electra_trainer = fine_tune_model(electra_model, electra_tokenizer, dataset)

# Enregistrer le modèle et le tokenizer
output_dir = './electra_finetuned'
electra_model.save_pretrained(output_dir)
electra_tokenizer.save_pretrained(output_dir)

# Fine-tuning BERT
bert_trainer = fine_tune_model(bert_model, bert_tokenizer, dataset)



# Enregistrer le modèle et le tokenizer
output_dir = './bert_finetuned'
bert_model.save_pretrained(output_dir)
bert_tokenizer.save_pretrained(output_dir)

from datasets import load_metric

def evaluate_model(trainer):
    metric = load_metric("glue", "sst2")
    eval_result = trainer.evaluate() # Remove the metrics argument
    # Compute metrics if needed (refer to Hugging Face documentation for how to do this)
    print(f"A metric that is likely computed: {eval_result.keys()}")
    return eval_result

# Évaluation ELECTRA
print("ELECTRA Model Performance:")
electra_eval = evaluate_model(electra_trainer)

electra_eval

# Évaluation BERT
print("BERT Model Performance:")
bert_eval = evaluate_model(bert_trainer)

bert_eval

"""#Benchmark 2 - Memory Consumption - fonctionne, surement à densifier en faisant varier des paramètres en +"""

from transformers import ElectraForSequenceClassification, ElectraConfig, BertForSequenceClassification, BertConfig
import torch
import matplotlib.pyplot as plt
import evaluate

# Configuration d'ELECTRA
electra_config = ElectraConfig(
    hidden_size=256,
    num_attention_heads=4,
    num_hidden_layers=6,
    max_position_embeddings=1024,
    vocab_size=10000,
)
electra_model = ElectraForSequenceClassification(electra_config)

# Configuration de BERT
bert_config = BertConfig(
    hidden_size=256,
    num_attention_heads=4,
    num_hidden_layers=6,
    max_position_embeddings=1024,
    vocab_size=10000,
)
bert_model = BertForSequenceClassification(bert_config)

# Déplacer les modèles vers le GPU
electra_model.cuda()
bert_model.cuda()

# Générer des données d'entrée de différentes longueurs (jusqu'à 1024)
data = []
list_lengths = [128, 256, 512, 1024]
for L in list_lengths:
    input_ids = torch.randint(0, 10000, (1, L)).cuda()
    data.append(input_ids)

# Mesurer la consommation de mémoire
def measure_memory_cost(model, data):
    memory_cost = []
    for input_ids in data:
        torch.cuda.empty_cache()
        outputs = model(input_ids=input_ids)
        memory_cost.append(torch.cuda.memory_allocated())
    return memory_cost

# Mesurer la consommation de mémoire pour ELECTRA et BERT
electra_memory_cost = measure_memory_cost(electra_model, data)
bert_memory_cost = measure_memory_cost(bert_model, data)

# Visualiser la consommation de mémoire
plt.figure(figsize=(8, 6))
plt.plot(list_lengths, electra_memory_cost, label='ELECTRA', linestyle='-')
plt.plot(list_lengths, bert_memory_cost, label='BERT', linestyle='--')

# Ajouter des labels, un titre, une grille et une légende
plt.xlabel('Input Sequence Length')
plt.ylabel('Memory Consumption (MB)')
plt.title('Memory Consumption vs Input Sequence Length for ELECTRA and BERT')
plt.grid(True)
plt.legend()
plt.show()

!pip install evaluate

"""#Benchmark 3- Blue Score - en cours, mais BERT et ELECTRA pas adaptés à traduction donc à voir."""

# Calculer et comparer les scores BLEU
bleu = evaluate.load("bleu")

def compute_bleu(reference, candidate):
    bleu_score = bleu.compute(references=[[reference]], predictions=[candidate])
    return bleu_score["bleu"]

# Exemple d'utilisation :
reference_text = "The quick brown fox jumps over the lazy dog."
candidate_text_electra = "The quick pink fox jumps over the sleeping dog."
candidate_text_bert = "The fast brown fox leaps over the lazy dog."

bleu_score_electra = compute_bleu(reference_text, candidate_text_electra)
bleu_score_bert = compute_bleu(reference_text, candidate_text_bert)

print(f"BLEU Score for ELECTRA: {bleu_score_electra}")
print(f"BLEU Score for BERT: {bleu_score_bert}")

from transformers import ElectraForSequenceClassification, ElectraTokenizer, BertForSequenceClassification, BertTokenizer
from datasets import load_dataset
import torch
import evaluate
import matplotlib.pyplot as plt

# Charger les modèles et tokenizers
electra_tokenizer = ElectraTokenizer.from_pretrained('google/electra-small-discriminator')
electra_model = ElectraForSequenceClassification.from_pretrained('google/electra-small-discriminator').cuda()

bert_tokenizer = BertTokenizer.from_pretrained('prajjwal1/bert-small')
bert_model = BertForSequenceClassification.from_pretrained('prajjwal1/bert-small').cuda()

# Charger le dataset WMT
dataset = load_dataset('wmt14', 'fr-en', split='test[:100]')

# Extrait des exemples de phrases en français et leurs traductions en anglais
source_sentences = [item['translation']['fr'] for item in dataset]
reference_sentences = [item['translation']['en'] for item in dataset]

bleu = evaluate.load("bleu")

def translate_and_compute_bleu(model, tokenizer, source_sentences, reference_sentences):
    translations = []
    for sentence in source_sentences:
        inputs = tokenizer(sentence, return_tensors='pt', truncation=True, padding=True).input_ids.cuda()
        outputs = model(inputs)
        predicted_ids = torch.argmax(outputs.logits, dim=-1)
        translation = tokenizer.decode(predicted_ids[0], skip_special_tokens=True)
        translations.append(translation)

    bleu_score = bleu.compute(references=[[ref] for ref in reference_sentences], predictions=translations)
    return bleu_score['bleu'], translations

# Traduire et calculer les scores BLEU pour ELECTRA
bleu_score_electra, translations_electra = translate_and_compute_bleu(electra_model, electra_tokenizer, source_sentences, reference_sentences)

# Traduire et calculer les scores BLEU pour BERT
bleu_score_bert, translations_bert = translate_and_compute_bleu(bert_model, bert_tokenizer, source_sentences, reference_sentences)

print(f"BLEU Score for ELECTRA: {bleu_score_electra}")
print(f"BLEU Score for BERT: {bleu_score_bert}")

# Exemples de traductions
for i in range(5):
    print(f"Source: {source_sentences[i]}")
    print(f"Reference: {reference_sentences[i]}")
    print(f"Translation ELECTRA: {translations_electra[i]}")
    print(f"Translation BERT: {translations_bert[i]}")
    print()

# Graphique des scores BLEU
models = ['ELECTRA', 'BERT']
bleu_scores = [bleu_score_electra, bleu_score_bert]

plt.figure(figsize=(8, 6))
plt.bar(models, bleu_scores, color=['blue', 'orange'])

# Ajouter des labels, un titre, une grille
plt.xlabel('Models')
plt.ylabel('BLEU Score')
plt.title('BLEU Scores for ELECTRA and BERT on WMT14 Dataset')
plt.grid(True)
plt.show()

"""#Benchmarck 4 - GLUE - SST2"""

from transformers import ElectraForSequenceClassification, ElectraTokenizer, BertForSequenceClassification, BertTokenizer, Trainer, TrainingArguments
from datasets import load_dataset
import torch
import evaluate
import matplotlib.pyplot as plt

# Charger les modèles et tokenizers
electra_tokenizer = ElectraTokenizer.from_pretrained('google/electra-small-discriminator')
electra_model = ElectraForSequenceClassification.from_pretrained('google/electra-small-discriminator').cuda()

bert_tokenizer = BertTokenizer.from_pretrained('prajjwal1/bert-small')
bert_model = BertForSequenceClassification.from_pretrained('prajjwal1/bert-small').cuda()

# Charger le dataset SST-2
dataset = load_dataset('glue', 'sst2')

# Split du dataset
train_dataset = dataset['train']
validation_dataset = dataset['validation']
test_dataset = dataset['test']

def preprocess_function(examples):
    return electra_tokenizer(examples['sentence'], truncation=True, padding='max_length', max_length=128)

encoded_train_dataset = train_dataset.map(preprocess_function, batched=True)
encoded_validation_dataset = validation_dataset.map(preprocess_function, batched=True)
encoded_test_dataset = test_dataset.map(preprocess_function, batched=True)

training_args = TrainingArguments(
    output_dir='./results',
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

electra_trainer = Trainer(
    model=electra_model,
    args=training_args,
    train_dataset=encoded_train_dataset,
    eval_dataset=encoded_validation_dataset,
)

electra_trainer.train()

bert_trainer = Trainer(
    model=bert_model,
    args=training_args,
    train_dataset=encoded_train_dataset,
    eval_dataset=encoded_validation_dataset,
)

bert_trainer.train()

electra_results = electra_trainer.evaluate(eval_dataset=encoded_validation_dataset)
print(f"ELECTRA Evaluation Results: {electra_results}")

bert_results = bert_trainer.evaluate(eval_dataset=encoded_validation_dataset)
print(f"BERT Evaluation Results: {bert_results}")

# Récupérer les pertes d'évaluation
electra_loss = electra_results['eval_loss']
bert_loss = bert_results['eval_loss']

# Visualiser les résultats
models = ['ELECTRA', 'BERT']
losses = [electra_loss, bert_loss]

plt.figure(figsize=(8, 6))
plt.bar(models, losses, color=['blue', 'orange'])

# Ajouter des labels, un titre, une grille
plt.xlabel('Models')
plt.ylabel('Loss')
plt.title('Evaluation Loss for ELECTRA and BERT on SST-2 Dataset')
plt.grid(True)
plt.show()

"""#Benchmark 5

##MNLI (Multi-Genre Natural Language Inference) :

Tâche : Classification des paires de phrases en entailment, contradiction, ou neutral.
Dataset : glue, mnli.
"""

from transformers import ElectraForSequenceClassification, ElectraTokenizer, BertForSequenceClassification, BertTokenizer, Trainer, TrainingArguments
from datasets import load_dataset, load_metric
import torch
import matplotlib.pyplot as plt

# Charger les modèles et tokenizers
electra_tokenizer = ElectraTokenizer.from_pretrained('google/electra-small-discriminator')
electra_model = ElectraForSequenceClassification.from_pretrained('google/electra-small-discriminator').cuda()

bert_tokenizer = BertTokenizer.from_pretrained('prajjwal1/bert-small')
bert_model = BertForSequenceClassification.from_pretrained('prajjwal1/bert-small').cuda()

# Charger le dataset MNLI
dataset = load_dataset('glue', 'mnli')

# Split du dataset
train_dataset = dataset['train']
validation_matched_dataset = dataset['validation_matched']
validation_mismatched_dataset = dataset['validation_mismatched']

def preprocess_function(examples):
    return electra_tokenizer(examples['premise'], examples['hypothesis'], truncation=True, padding='max_length', max_length=128)

encoded_train_dataset = train_dataset.map(preprocess_function, batched=True)
encoded_validation_matched_dataset = validation_matched_dataset.map(preprocess_function, batched=True)
encoded_validation_mismatched_dataset = validation_mismatched_dataset.map(preprocess_function, batched=True)

training_args = TrainingArguments(
    output_dir='./results',
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

electra_trainer = Trainer(
    model=electra_model,
    args=training_args,
    train_dataset=encoded_train_dataset,
    eval_dataset=encoded_validation_matched_dataset,
)

electra_trainer.train()

bert_trainer = Trainer(
    model=bert_model,
    args=training_args,
    train_dataset=encoded_train_dataset,
    eval_dataset=encoded_validation_matched_dataset,
)

bert_trainer.train()

accuracy_metric = load_metric("accuracy")

# Fonction de calcul des métriques
def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)
    return accuracy_metric.compute(predictions=predictions, references=labels)

electra_trainer.compute_metrics = compute_metrics
electra_results = electra_trainer.evaluate(eval_dataset=encoded_validation_matched_dataset)
print(f"ELECTRA Evaluation Results: {electra_results}")

bert_trainer.compute_metrics = compute_metrics
bert_results = bert_trainer.evaluate(eval_dataset=encoded_validation_matched_dataset)
print(f"BERT Evaluation Results: {bert_results}")

# Récupérer les métriques d'évaluation
electra_accuracy = electra_results['eval_accuracy']
bert_accuracy = bert_results['eval_accuracy']

# Visualiser les résultats
models = ['ELECTRA', 'BERT']
accuracies = [electra_accuracy, bert_accuracy]

plt.figure(figsize=(8, 6))
plt.bar(models, accuracies, color=['blue', 'orange'])

# Ajouter des labels, un titre, une grille
plt.xlabel('Models')
plt.ylabel('Accuracy')
plt.title('Accuracy for ELECTRA and BERT on MNLI Dataset')
plt.grid(True)
plt.show()

"""#Test"""

from transformers import ElectraForSequenceClassification, ElectraTokenizer, BertForSequenceClassification, BertTokenizer, Trainer, TrainingArguments
from datasets import load_dataset, load_metric
import torch
import matplotlib.pyplot as plt

# Charger les modèles et tokenizers
electra_tokenizer = ElectraTokenizer.from_pretrained('google/electra-small-discriminator')
electra_model = ElectraForSequenceClassification.from_pretrained('google/electra-small-discriminator').cuda()

from transformers import ElectraConfig, ElectraModel

# Initializing a ELECTRA electra-base-uncased style configuration
configuration = ElectraConfig()

# Initializing a model (with random weights) from the electra-base-uncased style configuration
model = ElectraModel(configuration)

# Accessing the model configuration
configuration = model.config

#Définition des états du modèle :

configuration.number_
configuration.hidden_size = 128
configuration.num_hidden_layers = 6
configuration.num_attention_heads = 4
configuration.max_position_embeddings = 1024
configuration.vocab_size = 10000