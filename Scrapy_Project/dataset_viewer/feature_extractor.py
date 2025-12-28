import pandas as pd
import re

class SpecExtractor:
    """
    Heuristics to extract PC specs from unstructured text.
    Focuses on CPU Generation (e.g. Intel 12th Gen, Ryzen 5000 Series).
    """

    @staticmethod
    def _find_ram(text):
        if not isinstance(text, str): return None
        # Pattern: Number (4-128) followed by GB and optional keywords
        pattern = r'\b(\d{1,3})\s*GB(?:\s*(?:RAM|DDR|Arbeitsspeicher)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            val = int(m)
            # Heuristic: RAM is usually between 4 and 128 GB.
            if 4 <= val <= 128:
                return val
        return None

    @staticmethod
    def _find_ssd(text):
        if not isinstance(text, str): return None
        
        # 1. Check for TB
        tb_pattern = r'\b(\d{1,2})\s*TB'
        match_tb = re.search(tb_pattern, text, re.IGNORECASE)
        if match_tb:
            return int(match_tb.group(1)) * 1000

        # 2. Check for GB (>= 120GB to distinguish from RAM)
        gb_pattern = r'\b(\d{3,4})\s*GB'
        matches_gb = re.findall(gb_pattern, text, re.IGNORECASE)
        for m in matches_gb:
            val = int(m)
            if val >= 120:
                return val
        return None

    @staticmethod
    def _find_cpu_gen(text):
        if not isinstance(text, str): return None
        
        # --- 1. INTEL GENERATION ---
        # Matches: i5-12400, i7 8700k, i5-1135G7, i7-6700HQ
        # Regex explanation:
        # i[3579]      -> Looks for i3, i5, i7, i9
        # [\s-]*       -> Optional separator
        # (\d{3,5})    -> Captures the model number (3 to 5 digits)
        intel_pattern = r'i[3579][\s-]*(\d{3,5})'
        match_intel = re.search(intel_pattern, text, re.IGNORECASE)
        
        if match_intel:
            model_str = match_intel.group(1)
            length = len(model_str)
            gen = None

            # Logic to decipher Generation from Model Number
            if length == 3:
                # e.g., i7-920 -> 1st Gen
                gen = "01"
            elif length >= 4:
                # Check the first two digits to see if it's 10, 11, 12, 13, 14...
                # e.g., 12700 (Gen 12), 1235U (Gen 12), 10700 (Gen 10)
                prefix_2 = int(model_str[:2])
                if 10 <= prefix_2 <= 19:
                    gen = str(prefix_2)
                else:
                    # Otherwise, it's a single digit generation (2nd to 9th)
                    # e.g., 8550U (Gen 8), 4790k (Gen 4), 6700 (Gen 6)
                    gen = "0" + model_str[0]
            
            if gen:
                return f"Intel Gen {gen}"

        # --- 2. AMD RYZEN SERIES ---
        # Matches: Ryzen 5 3600, Ryzen 7 5800H, Ryzen 7 7840U, Ryzen 5 5600
        # Regex explanation:
        # Ryzen          -> Keyword
        # (?:[\s-]*[3579])? -> Optional "5", "7" etc (non-capturing)
        # [\s-]+         -> Separator
        # (\d{4})        -> Captures the 4-digit model number
        amd_pattern = r'Ryzen(?:[\s-]*[3579])?[\s-]+(\d{4})'
        match_amd = re.search(amd_pattern, text, re.IGNORECASE)
        
        if match_amd:
            model_str = match_amd.group(1)
            # The first digit indicates the series (e.g., 5800 -> 5000 series)
            series = model_str[0]
            return f"AMD Ryzen {series}000 Series"

        return None

def enrich_dataframe(df):
    """
    Main function to be called from the Viewer.
    """
    
    def extract_row(row):
        title = str(row.get('Artikelstitel', ''))
        desc = str(row.get('Artikelsbeschreibung', ''))
        
        # 1. RAM
        ram = SpecExtractor._find_ram(title)
        if not ram: ram = SpecExtractor._find_ram(desc)
        
        # 2. SSD
        ssd = SpecExtractor._find_ssd(title)
        if not ssd: ssd = SpecExtractor._find_ssd(desc)

        # 3. CPU GENERATION (Updated)
        cpu = SpecExtractor._find_cpu_gen(title)
        if not cpu: cpu = SpecExtractor._find_cpu_gen(desc)
        
        return pd.Series([ram, ssd, cpu])

    # Add columns
    df[['Ext_RAM', 'Ext_SSD', 'Ext_CPU']] = df.apply(extract_row, axis=1)
    
    return df