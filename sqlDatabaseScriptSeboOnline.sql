CREATE TABLE users (
  idusers int NOT NULL AUTO_INCREMENT,
  name varchar(45) DEFAULT NULL,
  email varchar(45) DEFAULT NULL,
  password varchar(256) DEFAULT NULL,
  usertype varchar(45) DEFAULT NULL,
  status varchar(45) DEFAULT NULL,
  PRIMARY KEY (idusers)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO users VALUES (1,'root','root@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','admin','ativo'),(3,'mudei o nome paulo','novo@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','vendedor','ativo'),(4,'test','novo@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','vendedor','ativo'),(5,'mudei o teste','testei@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','comprador','deactivated'),(6,'mudei o teste','testei@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','comprador','ativo'),(7,'testei','paulopaulo@email.com','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','vendedor','ativo');

CREATE TABLE items (
  iditems int NOT NULL AUTO_INCREMENT,
  titulo varchar(45) DEFAULT NULL,
  autor varchar(45) DEFAULT NULL,
  categoria varchar(45) DEFAULT NULL,
  preco int DEFAULT NULL,
  status varchar(45) DEFAULT NULL,
  PRIMARY KEY (iditems)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO items VALUES (1,'AI at the Edge','Daniel Situnayake e Jenny Plunkett','Livro',322,'deactivated'),(2,'AI at the Edge','Daniel Situnayake e Jenny Plunkett','Livro',500,'ATIVO'),(3,'AI at the Edge','Daniel Situnayake e Jenny Plunkett','Livro',500,'INATIVO'),(4,'Livro teste','um bom autor','Livro',1000,'ATIVO'),(5,'Livro teste parte 2','um bom autor','Livro',1000,'ATIVO'),(6,'Diario de um banana','um bom autor banana','Livro',10000,'ATIVO');
