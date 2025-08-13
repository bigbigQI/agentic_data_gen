#!/usr/bin/env python3
"""
场景相似度过滤脚本
从场景数据中提取字符串，计算embedding相似度，筛选高相似度的字符串对
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple
from openai import OpenAI
from datetime import datetime


class ScenarioFilter:
    """场景相似度过滤器"""
    
    def __init__(self):
        """初始化客户端"""
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.similarity_threshold = 0.9
        self.batch_size = 10  # API一次最多请求10个
        
    def load_scenarios(self, file_path: str) -> List[Dict]:
        """加载场景数据"""
        print(f"Loading scenarios from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
        print(f"Loaded {len(scenarios)} scenarios")
        return scenarios
    
    def extract_strings(self, scenarios: List[Dict]) -> List[Dict[str, str]]:
        """提取name和use_cases组合的字符串"""
        strings = []
        
        for scenario in scenarios:
            name = scenario.get('name', '')
            use_cases = scenario.get('use_cases', [])
            
            # 组合name + use_case
            for i, use_case in enumerate(use_cases):
                combined_string = f"{name}+{use_case}"
                strings.append(combined_string)
        
        print(f"Extracted {len(strings)} combined strings")
        return strings
    
    def get_embeddings(self, strings: List[str]) -> List[List[float]]:
        """获取字符串的embedding"""
        all_embeddings = []
        
        # 分批处理
        for i in range(0, len(strings), self.batch_size):
            batch = strings[i:i + self.batch_size]
            print(f"Processing batch {i//self.batch_size + 1}/{(len(strings) + self.batch_size - 1)//self.batch_size}")
            
            try:
                response = self.client.embeddings.create(
                    model="text-embedding-v4",
                    input=batch,
                    dimensions=256,
                    encoding_format="float"
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Error processing batch: {e}")
                # 为失败的批次填充零向量
                batch_embeddings = [[0.0] * 256 for _ in batch]
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # 计算余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_pairs(self, strings_data: List[Dict], embeddings: List[List[float]]) -> List[Dict]:
        """找出相似度超过阈值的字符串对"""
        similar_pairs = []
        n = len(strings_data)
        
        print(f"Computing similarities for {n} strings...")
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self.cosine_similarity(embeddings[i], embeddings[j])
                
                if similarity > self.similarity_threshold:
                    similar_pairs.append({
                        'string1': strings_data[i],
                        'string2': strings_data[j],
                        'similarity': similarity,
                    })
        
        print(f"Found {len(similar_pairs)} similar pairs (similarity > {self.similarity_threshold})")
        return similar_pairs

    def save_embeddings(self, strings_data: List[str], embeddings: List[List[float]]):
        """保存embedding到文件（包含字符串和embedding）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        embeddings_file = f"data/generated/scenarios/embeddings_{timestamp}.json"
        embeddings_data = []
        for i, string_info in enumerate(strings_data):
            embeddings_data.append({
                'string': string_info,
                'embedding': embeddings[i]
            })
        
        os.makedirs(os.path.dirname(embeddings_file), exist_ok=True)
        with open(embeddings_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
        print(f"Embeddings saved: {embeddings_file}")
    
    def save_results(self, similar_pairs: List[Dict]):
        """保存结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 保存相似对
        similar_pairs_file = f"data/generated/scenarios/similar_pairs_{timestamp}.json"
        with open(similar_pairs_file, 'w', encoding='utf-8') as f:
            json.dump(similar_pairs, f, ensure_ascii=False, indent=2)
        
        print(f"Results saved:")
        print(f"  - Similar pairs: {similar_pairs_file}")
    
    def run(self, input_file: str):
        """运行完整的过滤流程"""
        print("=" * 60)
        print("场景相似度过滤开始")
        print("=" * 60)
        
        # 1. 加载场景数据
        scenarios = self.load_scenarios(input_file)
        
        # 2. 提取字符串
        strings_data = self.extract_strings(scenarios)
        
        # 3. 获取embedding
        print(f"Getting embeddings for {len(strings_data)} strings...")
        embeddings = self.get_embeddings(strings_data)
        self.save_embeddings(strings_data, embeddings)

        # 4. 计算相似度并筛选
        similar_pairs = self.find_similar_pairs(strings_data, embeddings)
        
        # 5. 保存结果
        self.save_results(similar_pairs)
        
        # 6. 打印摘要
        print("\n" + "=" * 60)
        print("处理完成！")
        print(f"总字符串数: {len(strings_data)}")
        print(f"相似对数量: {len(similar_pairs)}")
        print(f"相似度阈值: {self.similarity_threshold}")
        print("=" * 60)
        
        return similar_pairs


def main():
    """主函数"""
    # 检查环境变量
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("错误: 请设置环境变量 DASHSCOPE_API_KEY")
        return
    
    # 输入文件路径
    input_file = "data/generated/scenarios/scenarios_batch_20250803_212444.json"
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在 {input_file}")
        return
    
    # 运行过滤器
    filter_tool = ScenarioFilter()
    similar_pairs = filter_tool.run(input_file)
    
    # 显示前几个相似对的示例
    if similar_pairs:
        print("\n前5个相似对示例:")
        for i, pair in enumerate(similar_pairs[:5]):
            print(f"\n{i+1}. 相似度: {pair['similarity']:.4f}")
            print(f"   字符串1: {pair['string1']}")
            print(f"   字符串2: {pair['string2']}")


if __name__ == "__main__":
    main()