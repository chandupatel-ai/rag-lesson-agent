# Introduction to Retrieval‑Augmented Generation (RAG)

---  

## What is RAG?  

**Retrieval‑Augmented Generation** (**RAG**) is a way for a computer to answer questions **by first finding real text** and then writing a response.  
Think of a student who first opens a textbook, reads the relevant page, and then writes the answer.  

RAG has two clear parts  

1. **Retrieval** – find the most useful pieces of text for the question.  
2. **Generation** – let a large language model write an answer that uses those pieces.  

A **large language model** (**LLM**) is a computer program that can read and write natural language. It learns from huge amounts of text and can generate sentences that sound human‑like.  

---

## Why does it matter?  

Plain LLMs have three important limits  

| Limit | What it means | Why it is a problem |
|-------|---------------|---------------------|
| **Knowledge cutoff** | The model only knows facts up to a certain date. | It cannot answer questions about recent events. |
| **No private data** | The model cannot see documents that belong to a company, school, or personal library. | It cannot answer questions that need those specific documents. |
| **Hallucination** | The model sometimes makes up facts that are not true. | Users may receive wrong information. |

When you ask a plain LLM about a recent law, a company policy, or a detailed recipe, the model may guess.  
RAG solves this by **grounding** the answer in actual text that the system retrieved. The answer becomes more accurate and trustworthy.  

---

## How does it work?  

We will follow the standard RAG pipeline step by step.  

### 1. Gather the source documents  

Collect the books, articles, notes, or manuals that contain the knowledge you need.  
These are the **knowledge base** – the collection of text that the system can read.  

### 2. Split documents into **chunks**  

A **chunk** is a short piece of text, usually a paragraph or a few sentences.  
Chunking helps the system locate the exact part that matches a question.  

### 3. Turn every chunk into an **embedding**  

An **embedding** is a list of numbers that represents the meaning of a piece of text.  
Think of it as a fingerprint for a sentence.  
A small model (often called an **embedding model**) creates this fingerprint for each chunk.  

### 4. Store the embeddings in a **vector index**  

A **vector** is just another word for a list of numbers.  
A **vector index** is a searchable table that holds all the chunk fingerprints.  
When we later compare two vectors, we can see how similar their meanings are.  

### 5. Convert the user question into an embedding  

When you type a question, the same embedding model creates a fingerprint for that question.  

### 6. Perform **vector similarity search**  

**Vector similarity search** means comparing the question fingerprint with every chunk fingerprint.  
The system measures how close the numbers are.  
The chunks with the smallest distance (the most similar) are selected, usually the top three to five.  

### 7. Build a **prompt** for the large language model  

A **prompt** is the text we give to the LLM so it knows what to do.  
The prompt in RAG has three parts  

1. **Instruction** – a short command, e.g., “Answer the question using the information below.”  
2. **Retrieved chunks** – the pieces of text selected in step 6.  
3. **User question** – the original question you typed.  

### 8. Generate the final answer  

The LLM reads the prompt and writes a response.  
Because the prompt already contains real text, the LLM can copy facts, cite examples, and stay within the correct information.  

### 9. (Optional) Check the answer  

You may add a quick check: does the answer mention any of the retrieved chunks?  
If not, you can ask the LLM to try again with the same prompt.  

---

## Worked example  

### Situation  

You are a student preparing for a history exam.  
Your teacher gave you a PDF named *“Indian Independence Timeline”*.  
You want to know: **“When did India gain independence?”**  

### Step‑by‑step walk‑through  

1. **Gather documents** – Load the PDF into the system.  
2. **Chunk the PDF** – Split the PDF into separate paragraphs.  
   *Example chunk:* “On 15 August 1947, India became independent from British rule.”  
3. **Create embeddings** – Run the embedding model on every paragraph.  
   The example paragraph now has a numeric fingerprint.  
4. **Question embedding** – Convert the question “When did India gain independence?” into a fingerprint.  
5. **Vector similarity search** – Compare the question fingerprint with all paragraph fingerprints.  
   The system finds the paragraph about 15 August 1947 as the most similar.  
6. **Build the prompt**  

   ```
   Instruction: Answer the question using the information below.
   Retrieved text: On 15 August 1947, India became independent from British rule.
   Question: When did India gain independence?
   ```  

7. **Generate answer** – Send the prompt to the LLM.  
   The LLM replies: **“India gained independence on 15 August 1947.”**  
8. **Review** – Check that the answer uses the retrieved text.  
   The answer matches the paragraph, so it is correct.  

### What you see  

* The system **did not guess** the date.  
* It **used the exact sentence** from the source document.  
* The answer is short, clear, and trustworthy.  

---

## Key takeaways  

* **RAG = Retrieval + Generation.** First find real text, then write an answer.  
* Plain LLMs may give outdated or invented facts. RAG reduces those errors.  
* **Chunking** breaks large documents into small, searchable pieces.  
* **Embedding** is a numeric fingerprint that lets the computer compare meanings.  
* **Vector similarity search** picks the chunks that match the question best.  
* The **prompt** combines an instruction, the retrieved text, and the user question.  
* The final answer is **grounded** in actual information, making it more reliable.  

By following these steps, you can build a system that answers questions with the same care a student uses when looking up notes before an exam. This foundation is a solid first step toward a career in AI.