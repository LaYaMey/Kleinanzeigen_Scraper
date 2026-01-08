import pandas as pd
import re

class SpecExtractor:
    """
    Heuristics to extract PC specs from unstructured text.
    """

    @staticmethod
    def _find_ram(text):
        if not isinstance(text, str): return None
        pattern = r'\b(\d{1,3})\s*GB(?:\s*(?:RAM|DDR|Arbeitsspeicher)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            val = int(m)
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
        intel_pattern = r'i[3579][\s-]*(\d{3,5})'
        match_intel = re.search(intel_pattern, text, re.IGNORECASE)
        
        if match_intel:
            model_str = match_intel.group(1)
            length = len(model_str)
            gen = None

            if length == 3:
                gen = "01"
            elif length >= 4:
                prefix_2 = int(model_str[:2])
                if 10 <= prefix_2 <= 19:
                    gen = str(prefix_2)
                else:
                    gen = "0" + model_str[0]
            
            if gen:
                return f"Intel Gen {gen}"

        # --- 2. AMD RYZEN SERIES ---
        amd_pattern = r'Ryzen(?:[\s-]*[3579])?[\s-]+(\d{4})'
        match_amd = re.search(amd_pattern, text, re.IGNORECASE)
        
        if match_amd:
            model_str = match_amd.group(1)
            series = model_str[0]
            return f"AMD Ryzen {series}000 Series"

        return None

    @staticmethod
    def _find_gpu(text):
        """
        Detects specific NVIDIA RTX and GTX models.
        Returns strings like 'NVIDIA RTX 4060', 'NVIDIA RTX 3070 Ti', etc.
        """
        if not isinstance(text, str): return None
        
        t = text.upper() # Normalize to uppercase for easier matching
        
        # --- 1. NVIDIA RTX (20xx, 30xx, 40xx, 50xx) ---
        # Regex Explanation:
        # RTX          -> Literal match
        # \s*-?        -> Optional space or hyphen
        # (\d{4})      -> Group 1: Captures the 4-digit model (e.g. 4060)
        # (?: ... )?   -> Non-capturing optional group for the suffix
        # \s*          -> Optional space
        # (TI|SUPER)   -> Group 2: Captures 'TI' or 'SUPER'
        rtx_pattern = r'RTX\s*-?(\d{4})(?:\s*(TI|SUPER))?'
        rtx_match = re.search(rtx_pattern, t)
        
        if rtx_match:
            model = rtx_match.group(1)
            suffix = rtx_match.group(2)
            
            full_name = f"NVIDIA RTX {model}"
            if suffix:
                full_name += f" {suffix}"
            return full_name

        # --- 2. NVIDIA GTX (9xx, 10xx, 16xx) ---
        # Matches: GTX 1060, GTX 1660 Super, GTX 970
        gtx_pattern = r'GTX\s*-?(\d{3,4})(?:\s*(TI|SUPER))?'
        gtx_match = re.search(gtx_pattern, t)
        
        if gtx_match:
            model = gtx_match.group(1)
            suffix = gtx_match.group(2)
            
            full_name = f"NVIDIA GTX {model}"
            if suffix:
                full_name += f" {suffix}"
            return full_name

        return None

def enrich_dataframe(df):
    
    def extract_row(row):
        title = str(row.get('Artikelstitel', ''))
        desc = str(row.get('Artikelsbeschreibung', ''))
        
        # Helper to search title first, then desc
        def find_spec(func):
            res = func(title)
            if not res: res = func(desc)
            return res

        ram = find_spec(SpecExtractor._find_ram)
        ssd = find_spec(SpecExtractor._find_ssd)
        cpu = find_spec(SpecExtractor._find_cpu_gen)
        gpu = find_spec(SpecExtractor._find_gpu)
        
        return pd.Series([ram, ssd, cpu, gpu])

    # Add columns
    df[['Ext_RAM', 'Ext_SSD', 'Ext_CPU', 'Ext_GPU']] = df.apply(extract_row, axis=1)
    
    return df