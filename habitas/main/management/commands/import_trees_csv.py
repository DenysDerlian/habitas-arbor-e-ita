"""
Comando Django para importar árvores do CSV para o banco de dados.

Uso:
    python manage.py import_trees_csv
    python manage.py import_trees_csv --csv-path ../trees_all.csv
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Tree
from pathlib import Path
import csv
import re


class Command(BaseCommand):
    help = 'Importa árvores do arquivo CSV para o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default=None,
            help='Caminho para o arquivo CSV (padrão: ../trees_all.csv)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Pula árvores que já existem no banco (baseado em N_placa)',
        )

    def handle(self, *args, **options):
        """Executa a importação do CSV"""
        
        # Determina o caminho do CSV
        if options['csv_path']:
            csv_path = Path(options['csv_path'])
        else:
            # Caminho padrão: ../trees_all.csv relativo ao diretório do projeto
            csv_path = Path(__file__).parent.parent.parent.parent.parent / "trees_all.csv"
        
        if not csv_path.exists():
            self.stdout.write(
                self.style.ERROR(f'❌ Arquivo CSV não encontrado: {csv_path}')
            )
            return
        
        self.stdout.write(f'📂 Lendo arquivo: {csv_path}')
        
        # Obtém IDs já existentes se necessário
        existing_ids = set()
        if options['skip_existing']:
            existing_ids = set(Tree.objects.values_list('N_placa', flat=True))
            self.stdout.write(f'📊 Encontradas {len(existing_ids)} árvores já no banco')
        
        trees_to_create = []
        errors = []
        skipped = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file, delimiter=';')
                header = next(reader)  # Pula o cabeçalho
                
                self.stdout.write(f'📋 Cabeçalho: {header}')
                
                for row_num, row in enumerate(reader, start=2):
                    if len(row) < 10:
                        errors.append(f'Linha {row_num}: Número insuficiente de colunas')
                        continue
                    
                    try:
                        # Parse dos dados do CSV
                        # Formato: ID;Nome Popular;Nome Cientifico;DAP;Altura;Data Coleta;Latitude;Longitude;Laudos;Image Sources
                        tree_id = int(row[0])
                        
                        # Verifica se já existe
                        if options['skip_existing'] and tree_id in existing_ids:
                            skipped += 1
                            continue
                        
                        nome_popular = row[1].strip() if row[1] else ''
                        nome_cientifico = row[2].strip() if row[2] else ''
                        
                        # Parse DAP (remove "cm" se houver)
                        dap_str = row[3].strip() if row[3] else '0'
                        dap_match = re.search(r'(\d+)', dap_str)
                        dap = int(dap_match.group(1)) if dap_match else 0
                        
                        # Parse Altura (remove "m" se houver e converte vírgula para ponto)
                        altura_str = row[4].strip() if row[4] else '0'
                        altura_match = re.search(r'([\d,]+)', altura_str)
                        if altura_match:
                            altura_str = altura_match.group(1).replace(',', '.')
                            altura = float(altura_str)
                        else:
                            altura = 0.0
                        
                        # Parse Latitude e Longitude (converte vírgula para ponto)
                        latitude_str = row[6].strip() if row[6] else '0'
                        longitude_str = row[7].strip() if row[7] else '0'
                        latitude = float(latitude_str.replace(',', '.')) if latitude_str else 0.0
                        longitude = float(longitude_str.replace(',', '.')) if longitude_str else 0.0
                        
                        # Laudos e imagens (URLs)
                        laudos = row[8].strip() if row[8] else ''
                        imagens = row[9].strip() if row[9] else ''
                        
                        # Validação básica
                        if not nome_popular and not nome_cientifico:
                            errors.append(f'Linha {row_num}: Nome popular e científico vazios')
                            continue
                        
                        if dap <= 0 or altura <= 0:
                            errors.append(f'Linha {row_num}: DAP ou altura inválidos (DAP={dap}, Altura={altura})')
                            continue
                        
                        # Cria o objeto Tree (sem salvar ainda)
                        tree = Tree(
                            N_placa=tree_id,
                            nome_popular=nome_popular,
                            nome_cientifico=nome_cientifico,
                            dap=dap,
                            altura=altura,
                            latitude=latitude,
                            longitude=longitude,
                            laudo=laudos,
                            imagem=imagens,
                            plantado_por="Prefeitura de São José dos Campos",
                            origem='desconhecida'  # Valor padrão
                        )
                        
                        trees_to_create.append(tree)
                        
                        # Log a cada 1000 registros processados
                        if len(trees_to_create) % 1000 == 0:
                            self.stdout.write(f'  Processados: {len(trees_to_create)} árvores...')
                    
                    except ValueError as e:
                        errors.append(f'Linha {row_num}: Erro de conversão - {str(e)}')
                    except Exception as e:
                        errors.append(f'Linha {row_num}: Erro inesperado - {str(e)}')
            
            # Salva em lote usando bulk_create
            if trees_to_create:
                self.stdout.write(f'\n💾 Salvando {len(trees_to_create)} árvores no banco de dados...')
                
                # Usa bulk_create com ignore_conflicts para evitar erros de duplicatas
                created = Tree.objects.bulk_create(
                    trees_to_create,
                    ignore_conflicts=True,
                    batch_size=1000
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Importação concluída!'
                    )
                )
                self.stdout.write(f'   • {len(created)} árvores importadas')
                if skipped > 0:
                    self.stdout.write(f'   • {skipped} árvores puladas (já existentes)')
                if errors:
                    self.stdout.write(
                        self.style.WARNING(f'   • {len(errors)} erros encontrados')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Nenhuma árvore nova para importar.')
                )
                if skipped > 0:
                    self.stdout.write(f'   • {skipped} árvores já existiam no banco')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao processar CSV: {str(e)}')
            )
            import traceback
            traceback.print_exc()
            return
        
        # Mostra erros se houver
        if errors:
            self.stdout.write('\n📋 Primeiros 10 erros encontrados:')
            for error in errors[:10]:
                self.stdout.write(self.style.WARNING(f'   • {error}'))
            if len(errors) > 10:
                self.stdout.write(f'   ... e mais {len(errors) - 10} erros')

