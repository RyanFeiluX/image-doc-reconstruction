#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片文档重建脚本（Hermes版本）
将图片型PDF转换为结构化Markdown
使用百度OCR API进行文字识别

Hermes适配修改：
1. 用PyMuPDF替代pdf2image渲染PDF页面（无需poppler-utils sudo依赖）
2. 支持从环境变量读取百度OCR凭证
3. 便捷调用命令：pdf2md-baidu
"""

import os
import sys
import argparse
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from io import BytesIO
from collections import deque
import base64

# 依赖检查 —— 去除 pdf2image，用 PyMuPDF + Pillow 替代
try:
    import fitz  # PyMuPDF
    from PIL import Image
    from aip import AipOcr
except ImportError as e:
    print(f"错误：缺少必要的依赖库 {e}")
    print("请运行：pip install PyMuPDF Pillow baidu-aip")
    sys.exit(1)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def render_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[Image.Image]:
    """用PyMuPDF将PDF每页渲染为PIL图像（替代pdf2image，无需poppler-utils）

    Args:
        pdf_path: PDF文件路径
        dpi: 渲染DPI

    Returns:
        PIL图像列表
    """
    doc = fitz.open(pdf_path)
    images = []
    zoom = dpi / 72  # PyMuPDF默认72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    doc.close()
    return images


# ====== 以下代码继承自原Coze技能包，保持功能完整 ======

class TextNormalizer:
    """标点符号规范化器"""
    
    def __init__(self):
        self.ascii_to_cn = {
            '(': '（', ')': '）',
            '[': '【', ']': '】',
            '{': '｛', '}': '｝',
            ':': '：',
            '.': '。',
            ',': '，',
            ';': '；',
            '!': '！',
            '?': '？',
            '<': '《', '>': '》',
        }
        self.cn_to_ascii = {v: k for k, v in self.ascii_to_cn.items()}
    
    def detect_language(self, text: str) -> str:
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.strip()) or 1
        ratio = chinese_chars / total_chars
        if ratio > 0.3:
            return 'chinese'
        elif ratio < 0.1:
            return 'english'
        return 'mixed'
    
    def normalize(self, text: str) -> str:
        if not text or len(text.strip()) == 0:
            return text
        lang = self.detect_language(text)
        if lang == 'chinese':
            for ascii_char, cn_char in self.ascii_to_cn.items():
                text = text.replace(ascii_char, cn_char)
        elif lang == 'english':
            for cn_char, ascii_char in self.cn_to_ascii.items():
                text = text.replace(cn_char, ascii_char)
        return text


class HeadingNumberConsistency:
    """标题/列表编号一致性处理器"""
    
    def __init__(self):
        self.style_patterns = [
            (r'\((\d+)\)', 'parentheses'),
            (r'\（(\d+)\）', 'parentheses_cn'),
            (r'\【(\d+)\】', 'bracket_cn'),
            (r'\[(\d+)\]', 'bracket_ascii'),
            (r'^(\d+)\. ', 'dot'),
            (r'^([一二三四五六七八九十]+)\、', 'dot_cn'),
            (r'^-', 'dash'),
        ]
        self.style_counts = {}
    
    def detect_style(self, text: str) -> Optional[str]:
        for pattern, style_name in self.style_patterns:
            if re.search(pattern, text):
                return style_name
        return None
    
    def record_style(self, block_type: str, text: str):
        if not (block_type.startswith('heading') or block_type == 'list'):
            return
        style = self.detect_style(text)
        if not style:
            return
        if block_type not in self.style_counts:
            self.style_counts[block_type] = {}
        if style not in self.style_counts[block_type]:
            self.style_counts[block_type][style] = 0
        self.style_counts[block_type][style] += 1
    
    def get_dominant_style(self, block_type: str) -> Optional[str]:
        if block_type not in self.style_counts:
            return None
        styles = self.style_counts[block_type]
        if not styles:
            return None
        return max(styles.items(), key=lambda x: x[1])[0]
    
    def normalize_numbering(self, text: str, block_type: str, target_style: str) -> str:
        current_style = self.detect_style(text)
        if not current_style or current_style == target_style:
            return text
        
        if target_style == 'parentheses':
            text = re.sub(r'\【(\d+)\】', r'(\1)', text)
            text = re.sub(r'\[(\d+)\]', r'(\1)', text)
            text = re.sub(r'（(\d+)）', r'(\1)', text)
            text = re.sub(r'^(\d+)\. ', r'(\1) ', text)
            text = re.sub(r'^([一二三四五六七八九十]+)\、', r'(\1) ', text)
        elif target_style == 'parentheses_cn':
            text = re.sub(r'\((\d+)\)', r'（\1）', text)
            text = re.sub(r'\【(\d+)\】', r'（\1）', text)
            text = re.sub(r'\[(\d+)\]', r'（\1）', text)
            text = re.sub(r'^(\d+)\. ', r'（\1） ', text)
        elif target_style == 'bracket_cn':
            text = re.sub(r'\((\d+)\)', r'【\1】', text)
            text = re.sub(r'（(\d+)）', r'【\1】', text)
            text = re.sub(r'\[(\d+)\]', r'【\1】', text)
            text = re.sub(r'^(\d+)\. ', r'【\1】 ', text)
        elif target_style == 'bracket_ascii':
            text = re.sub(r'\((\d+)\)', r'[\1]', text)
            text = re.sub(r'（(\d+)）', r'[\1]', text)
            text = re.sub(r'\【(\d+)\】', r'[\1]', text)
            text = re.sub(r'^(\d+)\. ', r'[\1] ', text)
        elif target_style == 'dot':
            text = re.sub(r'\((\d+)\)', r'\1. ', text)
            text = re.sub(r'（(\d+)）', r'\1. ', text)
            text = re.sub(r'\【(\d+)\】', r'\1. ', text)
            text = re.sub(r'\[(\d+)\]', r'\1. ', text)
        return text


class BracketPairNormalizer:
    """括号配对规范化器"""
    
    def __init__(self):
        self.bracket_priority = [
            ('（', '）'),
            ('【', '】'),
            ('｛', '｝'),
            ('(', ')'),
            ('[', ']'),
            ('{', '}'),
        ]
    
    def detect_bracket_pairs(self, text: str) -> List[Dict]:
        patterns = [
            r'\(([^)]+)\)',
            r'（([^）]+）',
            r'【([^】]+)】',
            r'\[([^\]]+)\]',
            r'｛([^｝]+)｝',
            r'\{([^}]+)\}',
        ]
        pairs = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                pairs.append({
                    'left': text[match.start():match.start()+1],
                    'right': text[match.end()-1:match.end()],
                    'content': match.group(1),
                    'full_match': match.group(),
                })
        return pairs
    
    def check_consistency(self, pairs: List[Dict]) -> Dict[str, int]:
        stats = {
            'parentheses_cn': 0, 'parentheses_ascii': 0,
            'bracket_cn': 0, 'bracket_ascii': 0,
            'brace_cn': 0, 'brace_ascii': 0,
        }
        for pair in pairs:
            left, right = pair['left'], pair['right']
            if left == '（' and right == '）': stats['parentheses_cn'] += 1
            elif left == '(' and right == ')': stats['parentheses_ascii'] += 1
            elif left == '【' and right == '】': stats['bracket_cn'] += 1
            elif left == '[' and right == ']': stats['bracket_ascii'] += 1
            elif left == '｛' and right == '｝': stats['brace_cn'] += 1
            elif left == '{' and right == '}': stats['brace_ascii'] += 1
        return stats
    
    def find_dominant_style(self, stats: Dict[str, int]) -> Optional[Tuple[str, str]]:
        if not stats or all(v == 0 for v in stats.values()):
            return None
        for left, right in self.bracket_priority:
            if left == '（' and stats['parentheses_cn'] > 0: return ('（', '）')
            elif left == '【' and stats['bracket_cn'] > 0: return ('【', '】')
            elif left == '｛' and stats['brace_cn'] > 0: return ('｛', '｝')
            elif left == '(' and stats['parentheses_ascii'] > 0: return ('(', ')')
            elif left == '[' and stats['bracket_ascii'] > 0: return ('[', ']')
            elif left == '{' and stats['brace_ascii'] > 0: return ('{', '}')
        return None
    
    def normalize(self, text: str, target_style: Optional[Tuple[str, str]] = None) -> str:
        pairs = self.detect_bracket_pairs(text)
        if not pairs:
            return text
        if not target_style:
            stats = self.check_consistency(pairs)
            target_style = self.find_dominant_style(stats)
        if not target_style:
            return text
        target_left, target_right = target_style
        result = text
        for pair in reversed(pairs):
            left, right = pair['left'], pair['right']
            content = pair['content']
            if left == target_left and right == target_right:
                continue
            old_text = f"{left}{content}{right}"
            new_text = f"{target_left}{content}{target_right}"
            result = result.replace(old_text, new_text, 1)
        return result


class HeaderFooterPatternDetector:
    """页眉页脚模式探测器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            'header_ratio': 0.12,
            'footer_ratio': 0.12,
            'min_repeat': 3,
            'position_tolerance': 5,
        }
        if config:
            self.config.update(config)
        self.pattern_stats = {}
    
    def learn(self, blocks: List[Dict], page_size: Tuple[int, int]):
        page_width, page_height = page_size
        for block in blocks:
            position_key = self._get_position_key(block)
            text = block.get('text', '').strip()
            region = self._detect_region(block, page_height)
            if position_key not in self.pattern_stats:
                self.pattern_stats[position_key] = {'text': text, 'count': 0, 'region': region}
            self.pattern_stats[position_key]['count'] += 1
    
    def get_patterns(self) -> Dict[str, List[str]]:
        patterns = {'header': [], 'footer': []}
        for position, stats in self.pattern_stats.items():
            if stats['count'] >= self.config['min_repeat']:
                if stats['region'] == 'header':
                    patterns['header'].append(position)
                elif stats['region'] == 'footer':
                    patterns['footer'].append(position)
        return patterns
    
    def filter(self, blocks: List[Dict], page_size: Tuple[int, int]) -> List[Dict]:
        patterns = self.get_patterns()
        filtered = []
        for block in blocks:
            if not self._is_matching_pattern(block, patterns):
                filtered.append(block)
        return filtered
    
    def _get_position_key(self, block: Dict) -> str:
        center_x = block.get('center_x', 0)
        center_y = block.get('center_y', 0)
        return f"{center_x:.0f}_{center_y:.0f}"
    
    def _detect_region(self, block: Dict, page_height: int) -> str:
        center_y = block.get('center_y', 0)
        if center_y < page_height * self.config['header_ratio']:
            return 'header'
        elif center_y > page_height * (1 - self.config['footer_ratio']):
            return 'footer'
        return 'body'
    
    def _is_matching_pattern(self, block: Dict, patterns: Dict[str, List[str]]) -> bool:
        position_key = self._get_position_key(block)
        if position_key in patterns['header'] or position_key in patterns['footer']:
            return True
        for pattern_key in patterns['header'] + patterns['footer']:
            if self._is_position_close(block, pattern_key):
                return True
        return False
    
    def _is_position_close(self, block: Dict, pattern_key: str, tolerance: Optional[int] = None) -> bool:
        if tolerance is None:
            tolerance = self.config['position_tolerance']
        pattern_x, pattern_y = map(float, pattern_key.split('_'))
        return (abs(block['center_x'] - pattern_x) < tolerance and
                abs(block['center_y'] - pattern_y) < tolerance)


class AuxiliaryElementFilter:
    """辅助元素过滤器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            'header_ratio': 0.12,
            'footer_ratio': 0.12,
            'min_text_length': 20,
        }
        if config:
            self.config.update(config)
        self.filter_stats = {}
    
    def should_filter(self, text_block: Dict, page_index: int) -> Tuple[bool, str]:
        text = text_block.get('text', '').strip()
        if not text:
            return False, ''
        center_x = text_block.get('center_x', 0)
        center_y = text_block.get('center_y', 0)
        page_height = center_y * 2
        page_width = center_x * 2
        
        in_header = center_y < page_height * self.config['header_ratio']
        in_footer = center_y > page_height * (1 - self.config['footer_ratio'])
        in_corner = (center_x < page_width * 0.15 or center_x > page_width * 0.85) and in_header
        
        if self._is_separator(text):
            self._record_stats('separator')
            return True, 'separator'
        if in_footer and len(text) <= 10 and self._is_page_number(text):
            self._record_stats('page_number')
            return True, 'page_number'
        if in_corner and len(text) < 30:
            self._record_stats('logo')
            return True, 'logo'
        if in_header and len(text) <= self.config['min_text_length']:
            if self._is_header_keyword(text):
                self._record_stats('header_keyword')
                return True, 'header_keyword'
        if in_footer and len(text) <= self.config['min_text_length']:
            if self._is_footer_keyword(text):
                self._record_stats('footer_keyword')
                return True, 'footer_keyword'
        return False, ''
    
    def _is_separator(self, text: str) -> bool:
        cleaned = text.strip()
        if len(cleaned) < 3:
            return False
        if all(c == cleaned[0] for c in cleaned):
            return cleaned[0] in ['-', '=', '_', '~', '*']
        return False
    
    def _is_page_number(self, text: str) -> bool:
        patterns = [
            r'^\d{1,3}$',
            r'^-\s*\d{1,3}\s*-$',
            r'^第\d{1,3}页$',
            r'^Page\s+\d{1,3}$',
            r'^P\s*\.\s*\d{1,3}$',
        ]
        for pattern in patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _is_header_keyword(self, text: str) -> bool:
        keywords = ['confidential', 'draft', 'internal use only', '保密', '草稿', '内部使用']
        return text.lower().strip() in keywords
    
    def _is_footer_keyword(self, text: str) -> bool:
        patterns = [r'©', r'^all rights reserved$', r'^www\.', r'^http']
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _record_stats(self, reason: str):
        if reason not in self.filter_stats:
            self.filter_stats[reason] = 0
        self.filter_stats[reason] += 1
    
    def get_filter_stats(self) -> Dict[str, int]:
        return self.filter_stats.copy()


class PDFTypeDetector:
    """PDF类型检测器"""
    
    def __init__(self, text_density_threshold: float = 0.01):
        self.text_density_threshold = text_density_threshold
    
    def detect(self, pdf_path: Path) -> Dict:
        doc = fitz.open(str(pdf_path))
        page_results = []
        text_pages = 0
        image_pages = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_density = self._calculate_text_density(page)
            if text_density >= self.text_density_threshold:
                page_type = "text"
                text_pages += 1
            else:
                page_type = "image"
                image_pages += 1
            page_results.append({"page_num": page_num + 1, "type": page_type, "text_density": text_density})
        
        doc.close()
        total_pages = len(page_results)
        if text_pages == total_pages: overall_type = "text"
        elif image_pages == total_pages: overall_type = "image"
        else: overall_type = "mixed"
        
        result = {"overall_type": overall_type, "page_results": page_results,
                  "text_pages": text_pages, "image_pages": image_pages, "total_pages": total_pages}
        logger.info(f"PDF类型检测完成: {overall_type} (文本页: {text_pages}, 图片页: {image_pages})")
        return result
    
    def _calculate_text_density(self, page) -> float:
        text = page.get_text("text")
        char_count = len(text.strip())
        rect = page.rect
        page_area = rect.width * rect.height
        text_density = char_count / page_area if page_area > 0 else 0.0
        return text_density


class BaiduOCRClient:
    """百度OCR API客户端"""
    
    def __init__(self, app_id: str, api_key: str, secret_key: str, language='ch'):
        self.language = language
        self.client = AipOcr(app_id, api_key, secret_key)
        logger.info("百度OCR客户端初始化完成")
    
    def recognize_image(self, image: Image.Image, accurate: bool = True) -> List[Dict]:
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()
        
        try:
            if accurate:
                result = self.client.accurateGeneral(image_data, options={
                    "language_type": "CHN_ENG" if self.language == 'ch' else "ENG",
                    "detect_direction": "true",
                    "paragraph": "true"
                })
            else:
                result = self.client.general(image_data, options={
                    "language_type": "CHN_ENG" if self.language == 'ch' else "ENG",
                    "detect_direction": "true",
                    "paragraph": "true"
                })
            
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                raise Exception(f"百度OCR API错误[{result['error_code']}]: {error_msg}")
            
            words_result = result.get("words_result", [])
            blocks = []
            for item in words_result:
                text = item.get("words", "")
                location = item.get("location", {})
                left = location.get("left", 0)
                top = location.get("top", 0)
                width = location.get("width", 0)
                height = location.get("height", 0)
                bbox = [[left, top], [left + width, top], [left + width, top + height], [left, top + height]]
                font_size = height / 2.0 if height > 0 else 12.0
                center_x = left + width / 2.0
                center_y = top + height / 2.0
                blocks.append({
                    'text': text, 'bbox': bbox, 'center_x': center_x,
                    'center_y': center_y, 'font_size': font_size, 'type': 'paragraph'
                })
            return blocks
        except Exception as e:
            raise Exception(f"百度OCR识别失败: {e}")


class ImageDocReconstructor:
    """图片文档重建器"""
    
    def __init__(self, app_id: str, api_key: str, secret_key: str, include_figures=True,
                 language='ch', normalize_punctuation=True, filter_auxiliary=True, accurate_ocr=None):
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.include_figures = include_figures
        self.language = language
        self.font_stats = {}
        self.ocr_client = BaiduOCRClient(app_id, api_key, secret_key, language)
        self.text_normalizer = TextNormalizer()
        self.heading_consistency = HeadingNumberConsistency()
        self.bracket_normalizer = BracketPairNormalizer()
        self.filter_auxiliary = filter_auxiliary
        self.accurate_ocr = accurate_ocr
        self.header_footer_detector = None
        self.auxiliary_filter = AuxiliaryElementFilter() if filter_auxiliary else None
        self.normalize_punctuation = normalize_punctuation
    
    def _extract_figures_from_page(self, page, page_num: int, figures_dir: Path, embed: bool = True) -> List[Dict]:
        figures = []
        if not self.include_figures:
            return figures
        image_list = page.get_images(full=True)
        if not image_list:
            return figures
        
        for img_index, img in enumerate(image_list, 1):
            try:
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    figure_y = page.rect.height / 2
                    
                    if embed:
                        encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                        data_uri = f"data:image/{image_ext};base64,{encoded_data}"
                        figures.append({
                            'index': img_index, 'path': None, 'data_uri': data_uri,
                            'caption': f"Figure {img_index} on page {page_num}",
                            'bbox': (0, figure_y, 100, figure_y + 100),
                            'center_y': figure_y, 'embedded': True
                        })
                    else:
                        fig_filename = f"page{page_num}_fig{img_index}.{image_ext}"
                        fig_path = figures_dir / fig_filename
                        with open(fig_path, "wb") as f:
                            f.write(image_bytes)
                        figures.append({
                            'index': img_index, 'path': f"figures/{fig_filename}", 'data_uri': None,
                            'caption': f"Figure {img_index} on page {page_num}",
                            'bbox': (0, figure_y, 100, figure_y + 100),
                            'center_y': figure_y, 'embedded': False
                        })
            except Exception as e:
                logger.warning(f"提取插图失败 (page={page_num}, img={img_index}): {e}")
        return figures
    
    def _analyze_layout(self, page_image: Image.Image, page_num: int) -> List[Dict]:
        try:
            if self.accurate_ocr is not None:
                accurate = self.accurate_ocr
            elif self.filter_auxiliary:
                accurate = False
            else:
                accurate = True
            blocks = self.ocr_client.recognize_image(page_image, accurate=accurate)
            mode_name = "高精度" if accurate else "普通"
            logger.debug(f"页面 {page_num}: 使用{mode_name}OCR，识别到 {len(blocks)} 个文本块")
            return blocks
        except Exception as e:
            logger.error(f"页面 {page_num} OCR分析失败: {e}")
            return []
    
    def _classify_blocks(self, blocks: List[Dict], page_num: int) -> List[Dict]:
        if not blocks:
            return blocks
        font_sizes = [b['font_size'] for b in blocks]
        sorted_sizes = sorted(font_sizes, reverse=True)
        
        if sorted_sizes:
            h1_threshold = sorted_sizes[0] * 0.8
            h2_threshold = h1_threshold * 0.8
            h3_threshold = h2_threshold * 0.8
            
            for block in blocks:
                text = block['text'].strip()
                if block['font_size'] >= h1_threshold and len(text) < 100:
                    block['type'] = 'heading1'
                elif block['font_size'] >= h2_threshold and len(text) < 100:
                    block['type'] = 'heading2'
                elif block['font_size'] >= h3_threshold and len(text) < 100:
                    block['type'] = 'heading3'
                elif text.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    block['type'] = 'list'
                else:
                    block['type'] = 'paragraph'
        
        self._validate_heading_hierarchy(blocks, page_num)
        
        if self.normalize_punctuation:
            for block in blocks:
                block['text'] = self.text_normalizer.normalize(block['text'])
                self.heading_consistency.record_style(block['type'], block['text'])
        return blocks
    
    def _validate_heading_hierarchy(self, blocks: List[Dict], page_num: int):
        heading_sizes = {'heading1': [], 'heading2': [], 'heading3': []}
        for block in blocks:
            if block['type'] in heading_sizes:
                heading_sizes[block['type']].append(block['font_size'])
        avg_sizes = {}
        for level, sizes in heading_sizes.items():
            if sizes:
                avg_sizes[level] = sum(sizes) / len(sizes)
        
        if 'heading1' in avg_sizes and 'heading2' in avg_sizes:
            if avg_sizes['heading2'] > avg_sizes['heading1']:
                logger.warning(f"第 {page_num} 页: H2字体({avg_sizes['heading2']:.1f})>H1({avg_sizes['heading1']:.1f})，调整H2为paragraph")
                for block in blocks:
                    if block['type'] == 'heading2' and block['font_size'] > avg_sizes['heading1']:
                        block['type'] = 'paragraph'
        if 'heading2' in avg_sizes and 'heading3' in avg_sizes:
            if avg_sizes['heading3'] > avg_sizes['heading2']:
                logger.warning(f"第 {page_num} 页: H3字体({avg_sizes['heading3']:.1f})>H2({avg_sizes['heading2']:.1f})，调整H3为paragraph")
                for block in blocks:
                    if block['type'] == 'heading3' and block['font_size'] > avg_sizes['heading2']:
                        block['type'] = 'paragraph'
    
    def _update_global_font_stats(self, blocks: List[Dict]):
        for block in blocks:
            font_size = block['font_size']
            if block['type'].startswith('heading'):
                if font_size not in self.font_stats:
                    self.font_stats[font_size] = 0
                self.font_stats[font_size] += 1
    
    def _normalize_headings(self, blocks: List[Dict]) -> List[Dict]:
        if not self.font_stats:
            return blocks
        heading_sizes = sorted([fs for fs in self.font_stats.keys()], reverse=True)
        size_to_level = {}
        if len(heading_sizes) >= 1: size_to_level[heading_sizes[0]] = 'heading1'
        if len(heading_sizes) >= 2: size_to_level[heading_sizes[1]] = 'heading2'
        if len(heading_sizes) >= 3: size_to_level[heading_sizes[2]] = 'heading3'
        for block in blocks:
            if block['type'].startswith('heading'):
                font_size = block['font_size']
                if font_size in size_to_level:
                    block['type'] = size_to_level[font_size]
        return blocks
    
    def _apply_global_consistency(self, all_blocks: List[Dict]):
        logger.info("正在应用全局字符一致性...")
        all_bracket_pairs = []
        for block in all_blocks:
            pairs = self.bracket_normalizer.detect_bracket_pairs(block['text'])
            all_bracket_pairs.extend(pairs)
        stats = self.bracket_normalizer.check_consistency(all_bracket_pairs)
        dominant_bracket = self.bracket_normalizer.find_dominant_style(stats)
        
        for block_type in ['heading1', 'heading2', 'heading3', 'list']:
            dominant_numbering = self.heading_consistency.get_dominant_style(block_type)
            if not dominant_numbering:
                continue
            for block in all_blocks:
                if block['type'] == block_type:
                    block['text'] = self.heading_consistency.normalize_numbering(
                        block['text'], block_type, dominant_numbering
                    )
        
        if dominant_bracket:
            logger.info(f"统一括号配对为: {dominant_bracket[0]}...{dominant_bracket[1]}")
            for block in all_blocks:
                block['text'] = self.bracket_normalizer.normalize(block['text'], dominant_bracket)
    
    def _blocks_to_markdown(self, blocks: List[Dict], figures: List[Dict], page_num: int) -> str:
        if not blocks and not figures:
            return ""
        sorted_blocks = sorted(blocks, key=lambda b: b['center_y'])
        all_items = []
        all_items.extend([{'item_type': 'text', 'center_y': b['center_y'], **b} for b in sorted_blocks])
        all_items.extend([{'item_type': 'figure', 'center_y': f.get('center_y', 0), **f} for f in figures])
        all_items.sort(key=lambda x: x['center_y'])
        
        markdown_lines = []
        for item in all_items:
            if item['item_type'] == 'text':
                text = item['text'].strip()
                if not text: continue
                block_type = item.get('type', 'paragraph')
                if block_type == 'heading1': markdown_lines.append(f"\n# {text}\n")
                elif block_type == 'heading2': markdown_lines.append(f"\n## {text}\n")
                elif block_type == 'heading3': markdown_lines.append(f"\n### {text}\n")
                elif block_type == 'list': markdown_lines.append(f"- {text}")
                else: markdown_lines.append(f"{text}")
            elif item['item_type'] == 'figure':
                caption = item.get('caption', '')
                if item.get('embedded', False):
                    data_uri = item.get('data_uri', '')
                    if data_uri: markdown_lines.append(f"\n![{caption}]({data_uri})\n")
                else:
                    path = item.get('path', '')
                    if path: markdown_lines.append(f"\n![{caption}]({path})\n")
        return "\n".join(markdown_lines)
    
    def reconstruct_pdf(self, pdf_path: str, output_path: str, figures_dir: Optional[str] = None, embed_figures: bool = True):
        pdf_file = Path(pdf_path)
        output_file = Path(output_path)
        
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_file}")
        
        if self.include_figures and not embed_figures:
            if figures_dir is None:
                figures_dir = output_file.parent / "figures"
            else:
                figures_dir = Path(figures_dir)
            figures_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始处理PDF: {pdf_file}")
        logger.info(f"输出文件: {output_file}")
        
        # 检测PDF类型
        logger.info("正在检测PDF类型（文本型/图片型）...")
        pdf_type_detector = PDFTypeDetector()
        pdf_type_result = pdf_type_detector.detect(pdf_file)
        overall_type = pdf_type_result['overall_type']
        
        if overall_type == 'text':
            logger.info("检测到文本型PDF，使用直接文本提取方式（无需OCR）")
            self._reconstruct_text_pdf(pdf_file, output_file, figures_dir, embed_figures)
            return
        elif overall_type == 'image':
            logger.info("检测到图片型PDF，使用百度OCR API进行识别")
        else:
            logger.info(f"检测到混合型PDF，使用百度OCR API进行识别")
        
        # OCR处理流程
        logger.info("正在将PDF转换为图片...")
        images = render_pdf_to_images(str(pdf_file), dpi=200)
        logger.info(f"共 {len(images)} 页")
        
        pdf_doc = fitz.open(str(pdf_file))
        all_markdown = []
        all_blocks = []
        
        # 第一遍：页眉页脚模式探测
        if self.filter_auxiliary:
            logger.info("第一遍遍历：探测页眉页脚模式...")
            self.header_footer_detector = HeaderFooterPatternDetector()
            for page_num, image in enumerate(images, 1):
                try:
                    blocks = self._analyze_layout(image, page_num)
                    self.header_footer_detector.learn(blocks, image.size)
                except Exception as e:
                    logger.warning(f"探测阶段处理第 {page_num} 页失败: {e}")
                    continue
            patterns = self.header_footer_detector.get_patterns()
            logger.info(f"探测到 {len(patterns['header'])} 个页眉模式, {len(patterns['footer'])} 个页脚模式")
        
        # 第二遍：实际处理
        logger.info("第二遍遍历：处理并生成Markdown...")
        for page_num, image in enumerate(images, 1):
            logger.info(f"处理第 {page_num}/{len(images)} 页...")
            try:
                page = pdf_doc[page_num - 1]
                figures = self._extract_figures_from_page(page, page_num, figures_dir, embed_figures)
                blocks = self._analyze_layout(image, page_num)
                
                if self.filter_auxiliary and self.header_footer_detector:
                    blocks = self.header_footer_detector.filter(blocks, image.size)
                if self.filter_auxiliary and self.auxiliary_filter:
                    filtered_blocks = []
                    for block in blocks:
                        should_filter, reason = self.auxiliary_filter.should_filter(block, page_num)
                        if should_filter:
                            logger.debug(f"过滤 (第{page_num}页): {block['text'][:30]}... ({reason})")
                        else:
                            filtered_blocks.append(block)
                    blocks = filtered_blocks
                
                classified_blocks = self._classify_blocks(blocks, page_num)
                self._update_global_font_stats(classified_blocks)
                all_blocks.extend(classified_blocks)
                
                page_markdown = self._blocks_to_markdown(classified_blocks, figures, page_num)
                all_markdown.append(page_markdown)
            except Exception as e:
                logger.error(f"第 {page_num} 页处理失败: {e}，跳过该页")
                continue
        
        pdf_doc.close()
        
        # 全局标题标准化
        logger.info("正在进行全局标题标准化...")
        all_blocks = self._normalize_headings(all_blocks)
        
        # 全局字符一致性
        if self.normalize_punctuation:
            self._apply_global_consistency(all_blocks)
        
        # 输出
        final_markdown_content = "\n".join(all_markdown)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_markdown_content)
        
        logger.info(f"✓ 文档重建完成: {output_file}")
        logger.info(f"✓ 共处理 {len(images)} 页")
        
        if self.filter_auxiliary and self.auxiliary_filter:
            filter_stats = self.auxiliary_filter.get_filter_stats()
            if filter_stats:
                logger.info("✓ 辅助元素过滤统计:")
                for reason, count in sorted(filter_stats.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  - {reason}: {count}")
    
    def _reconstruct_text_pdf(self, pdf_path: Path, output_path: Path, figures_dir: Optional[Path], embed_figures: bool):
        pdf_doc = fitz.open(str(pdf_path))
        all_markdown = []
        all_blocks = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            logger.info(f"处理第 {page_num + 1}/{len(pdf_doc)} 页（文本提取）...")
            try:
                blocks = self._extract_text_blocks_from_page(page, page_num + 1)
                figures = self._extract_figures_from_page(page, page_num + 1, figures_dir, embed_figures)
                classified_blocks = self._classify_blocks(blocks, page_num + 1)
                self._update_global_font_stats(classified_blocks)
                all_blocks.extend(classified_blocks)
                page_markdown = self._blocks_to_markdown(classified_blocks, figures, page_num + 1)
                all_markdown.append(page_markdown)
            except Exception as e:
                logger.error(f"第 {page_num + 1} 页处理失败: {e}，跳过该页")
                continue
        
        pdf_doc.close()
        
        logger.info("正在进行全局标题标准化...")
        all_blocks = self._normalize_headings(all_blocks)
        if self.normalize_punctuation:
            self._apply_global_consistency(all_blocks)
        
        final_markdown_content = "\n".join(all_markdown)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown_content)
        
        logger.info(f"✓ 文档重建完成: {output_path}")
    
    def _extract_text_blocks_from_page(self, page, page_num: int) -> List[Dict]:
        text_dict = page.get_text("dict")
        blocks = []
        for item in text_dict.get("blocks", []):
            if "lines" not in item:
                continue
            for line in item.get("lines", []):
                line_text = ""
                line_bbox = None
                line_font_size = 0
                for span in line.get("spans", []):
                    line_text += span["text"]
                    if line_bbox is None:
                        line_bbox = span["bbox"]
                    else:
                        x0 = min(line_bbox[0], span["bbox"][0])
                        y0 = min(line_bbox[1], span["bbox"][1])
                        x1 = max(line_bbox[2], span["bbox"][2])
                        y1 = max(line_bbox[3], span["bbox"][3])
                        line_bbox = (x0, y0, x1, y1)
                    if span["size"] > line_font_size:
                        line_font_size = span["size"]
                if line_text.strip():
                    blocks.append({
                        'text': line_text.strip(),
                        'bbox': line_bbox,
                        'font_size': line_font_size,
                        'page_num': page_num
                    })
        return blocks



# Environment variable names for Baidu OCR credentials
ENV_BAIDU_APP_ID = 'BAIDU_OCR_APP_ID'
ENV_BAIDU_API_KEY = 'BAIDU_OCR_API_KEY'
ENV_BAIDU_SECRET_KEY = 'BAIDU_OCR_SECRET_KEY'

def main():
    parser = argparse.ArgumentParser(description='图片文档重建工具（百度OCR API）')
    parser.add_argument('--input', '-i', required=True, help='输入PDF文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出Markdown文件路径')
    parser.add_argument('--app-id', help='百度OCR APP_ID（或对应环境变量）')
    parser.add_argument('--api-key', help='百度OCR API Key（或对应环境变量）')
    parser.add_argument('--secret-key', help='百度OCR Secret Key（或对应环境变量）')
    parser.add_argument('--include-figures', action='store_true', default=True, help='包含插图（默认True）')
    parser.add_argument('--no-figures', dest='include_figures', action='store_false', help='不包含插图')
    parser.add_argument('--embed-figures', action='store_true', default=True, help='嵌入图片到Markdown（默认Base64嵌入）')
    parser.add_argument('--no-embed', dest='embed_figures', action='store_false', help='引用模式（保存为独立文件）')
    parser.add_argument('--language', choices=['zh', 'ch', 'en'], default='ch', help='OCR语言（默认ch）')
    parser.add_argument('--figures-dir', help='插图输出目录（仅非嵌入模式）')
    parser.add_argument('--normalize-punctuation', action='store_true', default=True, help='启用字符规范化（默认True）')
    parser.add_argument('--no-normalize', dest='normalize_punctuation', action='store_false', help='禁用字符规范化')
    parser.add_argument('--filter-auxiliary', action='store_true', default=True, help='启用页眉页脚过滤（默认True）')
    parser.add_argument('--no-filter', dest='filter_auxiliary', action='store_false', help='禁用页眉页脚过滤')
    parser.add_argument('--accurate-ocr', action='store_true', help='强制高精度OCR')
    
    args = parser.parse_args()
    
    app_id = args.app_id or os.environ.get(ENV_BAIDU_APP_ID)
    api_key = args.api_key or os.environ.get(ENV_BAIDU_API_KEY)
    secret_key = args.secret_key or os.environ.get(ENV_BAIDU_SECRET_KEY)
    
    if not app_id or not api_key or not secret_key:
        print("错误：缺少百度OCR API凭证")
        print("请通过以下方式提供：")
        print("  方式一：命令行参数 --app-id, --api-key, --secret-key")
        print("  方式二：设置对应的环境变量（详见 README）")
        print("\n获取凭证：https://console.bce.baidu.com/ai/")
        sys.exit(1)
    
    language = 'ch' if args.language in ['zh', 'ch'] else 'en'
    
    reconstructor = ImageDocReconstructor(
        app_id=app_id, api_key=api_key, secret_key=secret_key,
        include_figures=args.include_figures, language=language,
        normalize_punctuation=args.normalize_punctuation,
        filter_auxiliary=args.filter_auxiliary,
        accurate_ocr=args.accurate_ocr
    )
    
    try:
        reconstructor.reconstruct_pdf(
            pdf_path=args.input, output_path=args.output,
            figures_dir=args.figures_dir, embed_figures=args.embed_figures
        )
    except Exception as e:
        logger.error(f"文档重建失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
