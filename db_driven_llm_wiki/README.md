Building a database driven LLM Wiki

for local LLM model, install ollama: curl -fsSL https://ollama.com/install.sh | sh
Sample for testing the wiki creation

```
python src/cli.py create \
  --category "Physics" \
  --title "Quantum States" \
  --type "concept" \
  --tags "hardware,mechanics" \
  --source-file "quantum_notes.txt"
```