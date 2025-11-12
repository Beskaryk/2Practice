import os
import sys
import argparse
import yaml
import urllib.request
import gzip
import re
from typing import Dict, Any, Optional, List


class ConfigError(Exception):
    pass


class RepositoryError(Exception):
    pass


class PackageNotFoundError(Exception):
    pass


class ConfigLoader:
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.required_fields = [
        'package_name',
        'repository_url', 
        'test_repository_mode',  
        'package_version',
        'output_filename',       
        'ascii_tree_output',     
        'max_dependency_depth'
        ]
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_path is None:
            default_path = os.path.join(os.path.dirname(__file__), 'test.yaml')
            config_path = os.path.abspath(default_path)
        
        if not os.path.exists(config_path):
            raise ConfigError(f"Конф файл не найден: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigError(f"Ошибка парсинга YAML: {e}")
        except Exception as e:
            raise ConfigError(f"Ошибка чтения файла: {e}")

        self._validate_config()
        return self.config
    
    def _validate_config(self) -> None:
        if self.config is None:
            raise ConfigError("Конфигурационный файл пуст")
        
        for field in self.required_fields:
            if field not in self.config:
                raise ConfigError(f"Отсутствует поле: {field}")
        
        if self.config['max_dependency_depth'] < 1:
            raise ConfigError("Глубина анализа должна быть положительным числом")


class DependencyResolver:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def get_package_dependencies(self) -> List[str]:
        package_name = self.config['package_name']
        package_version = self.config['package_version']
        repo_url = self.config['repository_url']
        
        packages_content = self._download_packages_file(repo_url)
        package_info = self._find_package_info(packages_content, package_name, package_version)
        
        if not package_info:
            raise PackageNotFoundError(f"Пакет {package_name} версии {package_version} не найден")
        
        dependencies = self._extract_dependencies(package_info)
        return dependencies
    
    def _download_packages_file(self, repo_url: str) -> str:
        try:
            release = self.config.get('release', 'focal')
            architecture = self.config.get('architecture', 'amd64')
            component = self.config.get('component', 'main')
            
            packages_url = f"{repo_url}/dists/{release}/{component}/binary-{architecture}/Packages.gz" ## ЧЕКНУТЬ
             
            with urllib.request.urlopen(packages_url) as response:
                compressed_data = response.read()
            
            decompressed_data = gzip.decompress(compressed_data)
            return decompressed_data.decode('utf-8')
            
        except Exception as e:
            raise RepositoryError(f"Ошибка при загрузке файла: {e}")
    
    def _find_package_info(self, packages_content: str, package_name: str, package_version: str) -> Optional[str]:
        packages = packages_content.split('\n\n')
        
        for package_block in packages:
            if f"Package: {package_name}" in package_block:
                version_lines = [line for line in package_block.split('\n') if line.startswith('Version:')]
                if version_lines:
                    actual_version = version_lines[0].replace('Version:', '').strip()
                    if actual_version == package_version or package_version in actual_version:
                        return package_block
        
        return None
    
    def _extract_dependencies(self, package_info: str) -> List[str]:
        dependencies = []
        
        for line in package_info.split('\n'):
            if line.startswith('Depends:'):
                depends_content = line.replace('Depends:', '').strip()
                dependencies = self._parse_depends(depends_content)
                break
        
        return dependencies
    
    def _parse_depends(self, depends_content: str) -> List[str]:
        dependencies = []
        
        if not depends_content:
            return dependencies
        
        parts = re.split(r',\s*(?![^(]*\))', depends_content)
        
        for part in parts:
            alternatives = part.split('|')
            for alt in alternatives:
                package_match = re.match(r'^\s*([a-zA-Z0-9+\-\.]+)', alt.strip())
                if package_match:
                    package_name = package_match.group(1)
                    if package_name not in dependencies:
                        dependencies.append(package_name)
        
        return dependencies


class DependencyVisualizer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def display_config(self) -> None:
        print("Параметры конфигурации:\n")
        
        config_mapping = {
            'package_name': 'Имя анализируемого пакета',
            'repository_url': 'URL-адрес репозитория',
            'test_repository_mode': 'Режим работы с тестовым репозиторием',
            'package_version': 'Версия пакета',
            'output_filename': 'Имя файла с изображением графа',
            'ascii_tree_output': 'Режим вывода ASCII-дерева',
            'max_dependency_depth': 'Максимальная глубина анализа зависимостей'
        }
        
        for key, description in config_mapping.items():
            value = self.config.get(key, 'нет')
            print(f"{description:45}: {value}")
        print()
    
    def display_dependencies(self, dependencies: List[str]) -> None:
        package_name = self.config['package_name']
        package_version = self.config['package_version']
        
        print(f"Зависимости пакета {package_name}:\n")
        
        if not dependencies:
            print("Пакет не имеет зависимостей")
            return
        
        for i, dep in enumerate(dependencies, 1):
            print(f"{i:2}. {dep}")
        
        print(f"\nВсего зависимостей: {len(dependencies)}")
    
    def run_stage(self) -> None:
        self.display_config()
        
        try:
            resolver = DependencyResolver(self.config)
            dependencies = resolver.get_package_dependencies()
            self.display_dependencies(dependencies)
            
        except PackageNotFoundError as e:
            print(f"Ошибка: {e}")
            sys.exit(1)
        except RepositoryError as e:
            print(f"Ошибка репозитория: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            sys.exit(1)


def demonstrate_error_handling():
    print("Демонстрация ошибок")
    
    loader = ConfigLoader()
    
    test_cases = [
        {
            "name": "Несуществующий файл",
            "config_path": "none.yaml",
            "expected_error": "Конфигурационный файл не найден"
        },
        {
            "name": "Некорректный синтаксис YAML",
            "config_content": "invalid: toyota bmw yaml: : :",
            "expected_error": "Ошибка парсинга YAML"
        },
        {
            "name": "Отсутствуют обязательные поля",
            "config_content": {"name": "test"},
            "expected_error": "Отсутствует обязательное поле"
        },
        {
            "name": "Некорректная максимальная глубина",
            "config_content": {
                "package_name": "test",
                "repository_url": "http://test.com",
                "package_version": "1.0",
                "max_dependency_depth": 0
            },
            "expected_error": "Максимальная глубина анализа должна быть положительным числом"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test_case['name']}")
        
        try:
            if "config_content" in test_case:
                test_file = f"test_{i}.yaml"
                with open(test_file, 'w') as f:
                    yaml.dump(test_case["config_content"], f)
                loader.load_config(test_file)
                os.remove(test_file)
            else:
                loader.load_config(test_case["config_path"])
                
            print("Ошибки не были обработаны")
            
        except ConfigError as e:
            if test_case["expected_error"] in str(e):
                print(f"Ошибки обработаны: {e}")
            else:
                print(f"Обработана ошибка: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Анализатор зависимостей',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str
    )
    
    parser.add_argument(
        '--test-errors',
        action='store_true'
    )
    
    parser.add_argument(
        '--stage',
        action = 'store_true'
    )
    
    args = parser.parse_args()
    
    if args.test_errors:
        demonstrate_error_handling()
        return
    
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(args.config)
        visualizer = DependencyVisualizer(config)
        
        if args.stage:
            visualizer.run_stage()

        
    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()