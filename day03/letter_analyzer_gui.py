#!/usr/bin/env python3
"""
GUI Letter Distribution Analyzer
Uses the distribution_of_letters module to analyze text in a graphical interface.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from distribution_of_letters import letter_distribution, print_distribution
import io
import sys

class LetterDistributionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Letter Distribution Analyzer")
        self.root.geometry("800x600")
        
        # Create the main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Input label and text area
        ttk.Label(main_frame, text="Enter text to analyze:").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        
        self.text_input = scrolledtext.ScrolledText(
            main_frame, height=8, width=60, wrap=tk.WORD
        )
        self.text_input.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Analyze button
        self.analyze_button = ttk.Button(
            main_frame, text="Analyze Text", command=self.analyze_text
        )
        self.analyze_button.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # Results label and area
        ttk.Label(main_frame, text="Analysis Results:").grid(
            row=3, column=0, sticky=(tk.W, tk.N), pady=(0, 5)
        )
        
        # Results text area with monospace font for better formatting
        self.results_text = scrolledtext.ScrolledText(
            main_frame, height=15, width=60, wrap=tk.NONE, font=("Courier", 10)
        )
        self.results_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Make results read-only
        self.results_text.config(state=tk.DISABLED)
        
        # Add some sample text
        self.text_input.insert(tk.END, "Enter your text here to analyze letter distribution...")
        
        # Bind Enter key to analyze
        self.root.bind('<Control-Return>', lambda event: self.analyze_text())
        
    def analyze_text(self):
        # Get text from input area
        text = self.text_input.get("1.0", tk.END).strip()
        
        if not text or text == "Enter your text here to analyze letter distribution...":
            messagebox.showwarning("Warning", "Please enter some text to analyze.")
            return
        
        try:
            # Use the imported functions
            distribution, total = letter_distribution(text)
            
            # Capture the output of print_distribution
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            
            print_distribution(distribution, total)
            
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            
            # Display results
            self.results_text.config(state=tk.NORMAL)
            self.results_text.delete("1.0", tk.END)
            
            # Add header with input text info
            self.results_text.insert(tk.END, f"Input text: \"{text[:50]}{'...' if len(text) > 50 else ''}\"\n")
            self.results_text.insert(tk.END, f"Text length: {len(text)} characters\n\n")
            
            # Add the distribution results
            self.results_text.insert(tk.END, output)
            
            # Add summary if there are letters
            if total > 0:
                unique_letters = len(distribution)
                self.results_text.insert(tk.END, f"\nSummary: {unique_letters} unique letters found")
            
            self.results_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during analysis: {str(e)}")

def main():
    root = tk.Tk()
    app = LetterDistributionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()